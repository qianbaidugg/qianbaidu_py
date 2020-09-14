#!/usr/bin/python
# -*- coding: UTF-8 -*-
# /**************************************************************************
# * Copyright (c) 2020, 烽火技服-IT装备部
# * All rights reserved.
# *
# * 文件名称：views_query.py
# * 文件标识：
# * 摘　　要：经营情况跟踪-查询
# *
# * 当前版本：1.0
# * 原作者　：千百度
# * 完成日期：2020年7月
# * 修订记录：创建
# **************************************************************************/

import json, sys, traceback, time, copy, os, threading, datetime
from itertools import chain
from django.http import JsonResponse, StreamingHttpResponse
from django.db.models import Sum, Count,Aggregate, CharField, Q, F
from django.db import connection, connections
from django.core.serializers import serialize

from ..Logger import Logger
from manageTrace.modify.views import tokenCheck
from manageTrace.models import Item, Area, Character, Product, Personnel, ItemHis, PersonnelCharacter, Weight
from manageTrace.models import VItemSortByArea, VItemSortByProduct


## 查询函数列表 ##
fun_list = [
# --- 主页-产品 ---
'mainProductStatistics',            #产品主类统计：主设备，软件类
'allProductStatistics',             #主类型下产品统计：维保，网优…
'mainProductItemDetail',            #查询某人负责的产品详细信息
# -- 排名
'allItemSortByAreas',               #基于地区的团队项目完成情况排名
'allItemSortByProduct',             #基于产品的项目完成情况排名
# --主页-团队
'teamLeaderStatistics',             #团队组长的统计信息
'teamMemberStatistics',             #团队成员 的统计信息
'groupMemberAllStatistics',         #团队成员的总计详情
'groupMemberProductStatistics',     #团队成员各区域产品完成情况统计
'leader',                           #领导
'productDuty',                      #产品负责人
'allProductDuty',
'compare_by_area_all',              #区域比对：总计
'compare_by_area_id',               #区域比对：区域id
# 'areaLeaderlList',                  #区域负责人列表

# ---simple query-
'itemByitemid',
'itemByitemName',
'itemList',
'productByproductid',
'productByproductName',
'productList',
'personnelByPersonnelid',
'personnelByName',
'personnelList',
'areaByAreaid',
'areaByAreaName',
'areaList',
'characterBycharacterid',
'characterBycharacterName',
'characterList',
]
#下载日志
download_log = "download_log"

class Concat(Aggregate): # ORM用来分组显示其他字段 相当于group_concat
    function = 'GROUP_CONCAT'
    template = '%(function)s(%(distinct)s%(expressions)s)'

    def __init__(self, expression, distinct=False, **extra):
        super(Concat, self).__init__(
            expression,
            distinct='DISTINCT ' if distinct else '',
            output_field=CharField(),
            **extra)


log_debug = Logger('query.log', level='debug')
def write_debug(s):
    log_debug.logger.debug(s)


## 返回消息体
def make_err_rsp( msg1, msg2=''):
    ret_json = {'state': 1, 'context': []}
    ret_json['context'].append(msg1)
    ret_json['context'].append(msg2) if msg2 != '' else False
    return  ret_json

def make_succeed_rsp(s):
    db_ret = False
    ret_json = {'state': 0, 'context': []}
    json_data = serialize('json', s)
    json_data = json.loads(json_data)
    db_ret = True if len(json_data) > 0 else False

    [ ret_json['context'].append(ar['fields']) for ar in json_data]
    return db_ret, ret_json

def make_annotate_rsp(s, flist=False):
    db_ret = True
    ret_json = {'state': 0, 'context': []}
    if not flist and not s.exists():
        db_ret = False
        return db_ret, ret_json

    [ ret_json['context'].append(ar) for ar in s]
    return db_ret, ret_json

def append_s(l,s):#l:list, s:dict
    double_to_str(s, 'percent')
    l.append(s)

def double_to_str(a,key,n=2): #double, n:保留位数
    a[key] = str(str('%.' + str(n) +'f') % (int(100 * a[key] ) / 100.0))

def check_key_and_up(a,key): #a['item_money__sum']
    a.update({key: 0.0}) if key not in a.keys() else False

def calc_percent_and_2str(a):
    check_key_and_up(a, 'item_money__sum')
    check_key_and_up(a, 'item_money_fact__sum')
    p = 100 * a['item_money_fact__sum'] / a['item_money__sum'] if a['item_money__sum'] > 0.0 else 0.0
    a.update({'percent': p})
    double_to_str(a, 'item_money__sum')
    double_to_str(a, 'item_money_fact__sum')
    double_to_str(a, 'item_money_fact_thisweek') if 'item_money_fact_thisweek' in a.keys() else False
    double_to_str(a, 'item_frame_money') if 'item_frame_money' in a.keys() else False

    return a

def make_annotate_sort_rsp(ss, sort=False, flist=False):
    db_ret = True
    ret_json = {'state': 0, 'context': []}
    if not flist and not ss.exists():
        db_ret = False
        return db_ret, ret_json
    db_ret = True if len(ss) >0 else False
    for ar in ss:
        calc_percent_and_2str(ar)
        append_s(ret_json['context'], ar) if not sort else False
    if sort:
        st = sorted(ss, key=get_percent, reverse=True)
        [ append_s(ret_json['context'], ar) for ar in st]

    return db_ret, ret_json

def make_compare_rsp(ss ):
    db_ret = True if len(ss) else False
    ret_json = {'state': 0, 'context': []}
    for i in ss:
        for a in i['detail']:
            calc_percent_and_2str(a)
            double_to_str(a, 'percent')
        ret_json['context'].append(i)

    return db_ret, ret_json

def dup_area(a):
    s = a['area_name_sum']
    if s.rfind(',') == len(s) - 1:
        s = s[:-1]
    a['area_name_sum'] = '、'.join(list(set(s.split(','))))

def make_chainset_sort_rsp( ss, sort=False,area=True):
    db_ret = False
    ret_json = {'state': 0, 'context': []}
    tmp = []
    for ar in ss:
        db_ret = True
        calc_percent_and_2str(ar)
        dup_area(ar ) if area else False
        append_s(ret_json['context'], ar) if not sort else False
    if sort:
        st = sorted(ss, key=get_percent, reverse=True)
        [ append_s(ret_json['context'], ar) for ar in st]

    return db_ret, ret_json

def get_percent(s):
    return s['percent']

def deal_time(s):
    return " ".join(s.split())

def check_time(date):
    try:
        if ":" in date:
            time.strptime(date, "%Y-%m-%d %H:%M:%S")
        else:
            time.strptime(date, "%Y-%m-%d")
        return True
    except Exception as e:
        return False

def check_body(request):
    if not request.body:
        write_debug(u"request.body is NULL")
        ret_json = make_err_rsp(u"请求body不能为空")
        write_debug(ret_json)
        return False, ret_json
    else:
        req = json.loads(request.body)
        write_debug(req)
        return True, req

def get_current_week():
    last_saturday, friday = datetime.date.today(), datetime.date.today()
    one_day = datetime.timedelta(days=1)
    # ss = last_saturday.weekday()
    if last_saturday.weekday() != 0:
        while last_saturday.weekday() != 0:
            last_saturday -= one_day
        # last_saturday = calendar.SATURDAY - datetime.timedelta(days=7)
        last_saturday -= datetime.timedelta(days=2)
        friday = last_saturday + datetime.timedelta(days=6)
    else:
        last_saturday -= datetime.timedelta(days=9)
        friday = last_saturday + datetime.timedelta(days=6)

    # return monday, sunday
    # 返回时间字符串
    return datetime.datetime.strftime(last_saturday, "%Y-%m-%d") + ' 00:00:00', datetime.datetime.strftime(friday, "%Y-%m-%d")+ ' 23:59:59'


def combineTwoQuerySet(s1,s2,week=False):  ## 合并两条querySet数据（周详情）
    if week:
        ss = 'item_money_fact_thisweek'
    else:
        ss = 'item_money_fact__sum'
    for i in s1:
        i.update({ss: 0.0})
        for j in s2:
            if j['personnel_id'] == i['personnel_id']:
                i.update({ss: j[ss]})
                break
    return s1


def addPersonnelLeaderName(s):  ## 组长名字
    for i in s:
        ps = Personnel.objects.filter(personnel_id=i['personnel_id']).values('personnel_name')
        for j in ps:
            i.update({'personnel_name': j['personnel_name']})
    return s

''' request
{
“start_time”:”2020-01-10 16:03:13”,
“end_time”:”2020-12-10 16:03:13”,
“function”:”mainProductStatistics”
}
'''
''' response
{
    "state": 0,
    "context": [
        {
            "product_type": "软件类",
            "item_money__sum": 16000,
            "item_money_fact__sum": 14500,
            "percent": "90.62"
        },
        {
            "product_type": "主设备",
            "item_money__sum": 25000,
            "item_money_fact__sum": 15600,
            "percent": "62.40"
        }
    ]
}
'''
def mainProductStatistics(req):
    st = deal_time(req.get('start_time'))
    et = deal_time(req.get('end_time'))
    if not st or not et :
        return True, make_err_rsp(u"params: start_time or end_time needed")

    yst = get_current_year() + '-01-01 00:00:00'
    yet = get_current_year() + '-12-31 23:59:59'
    ss = []
    s1 = Product.objects.values('product_type').annotate(product_id_sum=Concat('product_id'))
    for i in s1:
        pids = []
        for x in i['product_id_sum'].split(','):
            pids.append(int(x))
        s2 = Item.objects.filter(item_flag =0, product_id__in=pids,item_record_time__range=[yst,yet]).aggregate(
            item_money__sum=Sum('item_money'))
        s2.update({'product_type': i['product_type']} )
        s3 = Item.objects.filter(item_flag__in=(2, 3), product_id__in=pids,item_record_time__range=[st,et]).aggregate(
            item_money_fact__sum=Sum('item_money_fact'))
        ps = s3['item_money_fact__sum'] if len(s3)> 0 else 0.0
        s2.update({'item_money_fact__sum': ps})
        ss.append(s2)

    return make_annotate_sort_rsp(ss, True, True)

''' request
{
“start_time”:”2020-01-10 16:03:13”,
“end_time”:”2020-12-10 16:03:13”,
“product_type”:”主设备”,
“function”:”allProductStatistics”
}
'''
''' response
-主设备
{
    "state": 0,
    "context": [
        {
            "product_type": "主设备",
            "product_id": 4,
            "product_name": "新业务",
            "name_comments": "(含CDN、哑资源、电子锁)",
            "personnel_id": "13",
            "personnel_name": "方昊",
            "item_money__sum": 4000,
            "item_money_fact__sum": 4400,
            "percent": "110.00"
        }
    ]
}
- 软件类
{
    "state": 0,
    "context": [
        {
            "product_type": "软件类",
            "product_id": 1,
            "product_name": "增值工具",
            "name_comments": "",
            "personnel_id": "6",
            "personnel_name": "构旭峰",
            "item_money__sum": 13000,
            "item_money_fact__sum": 12600,
            "percent": "96.92"
        }
    ]
}
'''
def allProductStatistics(req):
    st = deal_time(req.get('start_time'))
    et = deal_time(req.get('end_time'))
    ty = req.get('product_type')
    if not st or not et or not ty :
        return True, make_err_rsp(u"params: start_time, end_time or product_type needed")
    yst = get_current_year() + '-01-01 00:00:00'
    yet = get_current_year() + '-12-31 23:59:59'
    s1 = Product.objects.filter(product_type=ty).order_by('product_id')
    json_data = json.loads(serialize('json', s1))
    product_ids,personnel_ids,ss = [],[],[]
    for i in range(len(json_data)):
        ss.append(json_data[i]['fields'])
        product_ids.append(int(ss[i]['product_id']))
        personnel_ids.append(int(ss[i]['personnel']))
        ss[i]['personnel_id'] = ss[i].pop('personnel')
    s21 = Item.objects.values('product_id').filter(item_flag=0,product_id__in=product_ids,item_record_time__range=[yst, yet]
         ).annotate(item_money__sum=Sum('item_money') ).order_by('product_id')  # item_money_fact__sum=Sum('item_money_fact')
    s22 = Item.objects.values('product_id').filter(item_flag__in=(2, 3), product_id__in=product_ids,item_record_time__range=[st, et]
          ).annotate(item_money_fact__sum=Sum('item_money_fact')).order_by('product_id') #item_money__sum=Sum('item_money')
    s2 = merge_yearline_done(s21,s22,'product_id')
    s3 = Personnel.objects.filter(personnel_id__in=personnel_ids).values('personnel_id','personnel_name')
    for j in ss:
        for k in s2:
            if j['product_id'] == k['product_id']:
                j.update(k)
                break
        for a in s3:
            if j['personnel_id'] == a['personnel_id']:
                j.update({'personnel_name': a['personnel_name'] })
                break
        
    return make_annotate_sort_rsp(ss, True,True)
		
''' request
{
“start_time”:”2020-01-10 16:03:13”,
“end_time”:”2020-12-10 16:03:13”,
“personnel_name”:”吴文浩”,
“function”:”mainProductItemDetail”
}
'''

''' response
{
    "state": 0,
    "context": [
        {
            "product_type": "主设备",
            "product_id": 1,
            "product_name": "维保",
            "name_comments": "",
            "personnel_name": "",
            "personnel_id": "18672928722",
            "area_id": 1,
            "area_name": "福建",
            "item_id__count_type0_flag0": 3,
            "item_money__sum_type0_flag0": 589,
            "item_money_fact__sum_type0_flag0": 0,
            "item_id__count_type1_flag0": 0,
            "item_money__sum_type1_flag0": 0,
            "item_money_fact__sum_type1_flag0": 0,
            "item_id__count_type0_flag1": 0,
            "item_money__sum_type0_flag1": 0,
            "item_money_fact__sum_type0_flag1": 0,
            "item_id__count_type1_flag1": 6,
            "item_money__sum_type1_flag1": 0,
            "item_money_fact__sum_type1_flag1": 208.507108
        }
    ]
}
'''

res = {"product_type": "",
         "product_id": "",
         "product_name": "",
         "name_comments": "",
         "personnel_name": "",
         "personnel_id": "",
         "area_id": "",
         "area_name": "",
         "item_id__count_type0_flag0": 0,
         "item_money__sum_type0_flag0": 0,
         "item_money_fact__sum_type0_flag0": 0,
         "item_id__count_type1_flag0": 0,
         "item_money__sum_type1_flag0": 0,
         "item_money_fact__sum_type1_flag0": 0,
         "item_id__count_type0_flag1": 0,
         "item_money__sum_type0_flag1": 0,
         "item_money_fact__sum_type0_flag1": 0,
         "item_id__count_type1_flag1": 0,
         "item_money__sum_type1_flag1": 0,
         "item_money_fact__sum_type1_flag1": 0}


def mainProductItemDetail(req):
    st = deal_time(req.get('start_time'))
    et = deal_time(req.get('end_time'))
    ty = req.get('personnel_id') ## personnel_name to id
    if not st or not et or not ty :
        return True, make_err_rsp(u"params: start_time, end_time or personnel_name needed")

    yst = get_current_year() + '-01-01 00:00:00'
    yet = get_current_year() + '-12-31 23:59:59'
    db_ret = False
    ret_json = {'state': 0, 'context': []}
    sas = Area.objects.all().values('area_id', 'area_name').order_by('area_id')  #ps[0]['personnel_id']
    s1 = Product.objects.filter(personnel_id=ty).values('product_type', 'product_id','product_name','name_comments','personnel_id')
    for r in s1:
        # s0 = Item.objects.filter(item_record_time__range=[yst,yet],product_id=r['product_id'],
        #      item_flag__in=(0,3)).values('area_id').distinct().order_by('area_id')
        s00 = Item.objects.values('area_id').filter(item_record_time__range=[yst,yet],product_id=r['product_id'],item_type=0,
             item_flag=0).annotate(Count('item_id'),Sum('item_money'),Sum('item_money_fact')).values('area_id',
            item_money__sum_type0_flag0 = F('item_money__sum'),     #item_money_fact__sum_type0_flag0 = F('item_money_fact__sum'),
            item_id__count_type0_flag0=F('item_id__count')).order_by('area_id')
        s01 = Item.objects.values('area_id').filter(item_record_time__range=[st,et],product_id=r['product_id'],item_type=0,
             item_flag__in=(2,3)).annotate(Count('item_id'),Sum('item_money'),Sum('item_money_fact')).values('area_id',
            item_money_fact__sum_type0_flag1 = F('item_money_fact__sum'),   #item_money__sum_type0_flag1 = F('item_money__sum'),
            item_id__count_type0_flag1=F('item_id__count')).order_by('area_id')
        s10 = Item.objects.values('area_id').filter(item_record_time__range=[yst,yet],product_id=r['product_id'],item_type=1,
             item_flag=0).annotate(Count('item_id'),Sum('item_money'),Sum('item_money_fact')).values('area_id',
            item_money__sum_type1_flag0 = F('item_money__sum'),  #item_money_fact__sum_type1_flag0 = F('item_money_fact__sum'),
            item_id__count_type1_flag0=F('item_id__count')).order_by('area_id')
        s11 = Item.objects.values('area_id').filter(item_record_time__range=[st,et],product_id=r['product_id'],item_type=1,
             item_flag__in=(2,3)).annotate(Count('item_id'),Sum('item_money'),Sum('item_money_fact')).values('area_id',
            item_money_fact__sum_type1_flag1 = F('item_money_fact__sum'), #item_money__sum_type1_flag1 = F('item_money__sum'),
            item_id__count_type1_flag1=F('item_id__count')).order_by('area_id')
        #merge
        for j in sas:
            i = copy.deepcopy(res)
            i.update(r) #product info
            i.update(j) #area_id
            # merge_compare(sas, i, 'area_id') #name
            merge_compare(s00, i, 'area_id')
            merge_compare(s01, i, 'area_id')
            merge_compare(s10, i, 'area_id')
            merge_compare(s11, i, 'area_id')
            ret_json['context'].append(i)
        db_ret = True if len(ret_json['context']) > 0 else False
    return db_ret,ret_json

def merge_compare(o,d,k): # 源数据[{}]，目标{},key
    for a in o:
        if a[k] > d[k]:
            break
        if a[k] == d[k]:
            d.update(a)
            break
    return

''' request
{
“start_time”:”2020-01-10 16:03:13”,
“end_time”:”2020-12-10 16:03:13”,
“function”:”allItemSortByAreas”
}
'''

''' response
{
    "state": 0,
    "context": [
        {
            "personnel_id": "18626467415",
            "personnel_name": "张桓源",
            "item_money__sum": "8790.49",
            "item_money_fact__sum": "4668.47",
            "area_name_sum": "海外主设备、河南、江西、安徽",
            "item_money_fact_thisweek": "0.00",
            "percent": "53.11"
        },
        {
            "personnel_id": "15337200900",
            "personnel_name": "戚博",
            "item_money__sum": "6071.40",
            "item_money_fact__sum": "2774.78",
            "area_name_sum": "天津、河北、重庆、四川",
            "item_money_fact_thisweek": "0.00",
            "percent": "45.70"
        }
    ]
}
'''

def allItemSortByAreas(req):
    st1 = deal_time(req.get('start_time'))
    et1 = deal_time(req.get('end_time'))
    yst = get_current_year() + '-01-01 00:00:00'
    yet = get_current_year() + '-12-31 23:59:59'
    if not st1 or not et1:
        return True, make_err_rsp(u"时间未传入")
    ## 年度线索
    s11 = VItemSortByArea.objects.filter(item_flag=0, item_record_time__range=[yst, yet]).values(
        'personnel_id', 'personnel_name').annotate(Sum('item_money'), area_name_sum=Concat('area_name'))
    s12 = VItemSortByArea.objects.filter(item_flag=0, item_record_time__range=[yst, yet]).values(
        'personnel_leader_id').annotate(item_money__sum=Sum('item_money'), area_name_sum=Concat('area_name')).values(
        item_money__sum=F('item_money__sum'), area_name_sum=F('area_name_sum'), personnel_id=F('personnel_leader_id'))
    addPersonnelLeaderName(s12)
    ## 完成情况
    s13 = Item.objects.filter(item_record_time__range=[st1, et1], item_flag__in=(2, 3)).values('personnel_id').annotate(
        Sum('item_money_fact'))
    s14 = VItemSortByArea.objects.filter(item_record_time__range=[st1, et1], item_flag__in=(2, 3)).values(
        'personnel_leader_id').annotate(item_money_fact__sum=Sum('item_money_fact')).values(personnel_id=F('personnel_leader_id'
        ),item_money_fact__sum=F('item_money_fact__sum'))
    combineTwoQuerySet(s11, s13, False)
    combineTwoQuerySet(s12, s14, False)

    ## 周记录
    st2, et2 = get_current_week()
    s21 = Item.objects.filter(item_record_time__range=[st2, et2], item_flag__in=(2, 3)).values(
        'personnel_id').annotate(item_money_fact_thisweek=Sum('item_money_fact'))
    s22 = VItemSortByArea.objects.filter(item_record_time__range=[st2, et2], item_flag__in=(2, 3)).values(
        'personnel_leader_id').annotate(item_money_fact_thisweek=Sum('item_money_fact')).values(
        personnel_id=F('personnel_leader_id'), item_money_fact_thisweek=F('item_money_fact_thisweek'))
    ## 合并
    combineTwoQuerySet(s11, s21, True)
    combineTwoQuerySet(s12, s22, True)

    db1, rt1 = make_chainset_sort_rsp(s11, True, True)
    db2, rt2 = make_chainset_sort_rsp(s12, True, True)
    for i in rt2['context']:
        rt1['context'].append(i)

    return db1 or db2,rt1  #return make_chainset_sort_rsp(ss, True,True)

''' request
{
“start_time”:”2020-01-10 16:03:13”,
“end_time”:”2020-12-10 16:03:13”,
“function”:”allItemSortByProduct”
}
'''

''' response
{
    "state": 0,
    "context": [
        {
            "product_id": 4,
            "product_name": "备件",
            "name_comments": "",
            "personnel_id": "15827537524",
            "personnel_name": "唐国栋",
            "item_money__sum": "4558.05",
            "item_money_fact__sum": "2620.44",
            "item_money_fact_thisweek": "0.00",
            "percent": "57.49"
        }
    ]
}
'''
def allItemSortByProduct(req):
    st = deal_time(req.get('start_time'))
    et = deal_time(req.get('end_time'))
    if not st or not et:
        return True, make_err_rsp(u"时间未传入")

    yst = get_current_year() + '-01-01 00:00:00'
    yet = get_current_year() + '-12-31 23:59:59'
    ## 年度线索
    s1 = VItemSortByProduct.objects.values('product_id', 'product_name', 'name_comments', 'personnel_id',
        'personnel_name').filter(item_flag=0, item_record_time__range=[yst, yet]).annotate(
        Sum('item_money'))
    ## 周记录
    st2, et2 = get_current_week()
    s2 = VItemSortByProduct.objects.filter(item_record_time__range=[st2, et2], item_flag__in=(2, 3)).values(
        'personnel_id').annotate(item_money_fact_thisweek=Sum('item_money_fact'))
    ## 完成情况
    s3 = VItemSortByProduct.objects.filter(item_record_time__range=[st, et], item_flag__in=(2, 3)).values('personnel_id'
       ).annotate(Sum('item_money_fact'))

    ## 合并
    combineTwoQuerySet(s1, s3, False)
    combineTwoQuerySet(s1, s2, True)

    return make_annotate_sort_rsp(s1, True)

''' request
{
“start_time”:”2020-01-10 16:03:13”,
“end_time”:”2020-12-10 16:03:13”,
“function”:”teamLeaderStatistics”
}
'''

''' response
{
    "state": 0,
    "context": [
        {
            "item_money__sum": 15000,
            "item_money_fact__sum": 12500,
            "personnel_id": "3",
            "personnel_name": "王新洲",
            "percent": "83.33"
        },
        {
            "item_money__sum": 21000,
            "item_money_fact__sum": 13100,
            "personnel_id": "2",
            "personnel_name": "童庆武",
            "percent": "62.38"
        }
    ]
}
'''

def teamLeaderStatistics(req):
    st = deal_time(req.get('start_time'))
    et = deal_time(req.get('end_time'))
    if not st or not et:
        return True, make_err_rsp(u"params: start_time, end_time needed")

    yst = get_current_year() + '-01-01 00:00:00'
    yet = get_current_year() + '-12-31 23:59:59'
    s1 = VItemSortByArea.objects.values('personnel_leader_id').filter(item_flag=0,
        item_record_time__range=[yst,yet]).annotate(Sum('item_money'), Sum('item_money_fact')).values(
        item_money__sum = F('item_money__sum'),  # item_money_fact__sum = F('item_money_fact__sum'),
        personnel_id=F('personnel_leader_id'))
    s2 = VItemSortByArea.objects.values('personnel_leader_id').filter(item_flag__in=(2,3),
        item_record_time__range=[st,et]).annotate(Sum('item_money'), Sum('item_money_fact')).values( ## item_money__sum = F('item_money__sum'),
        item_money_fact__sum = F('item_money_fact__sum'),
        personnel_id=F('personnel_leader_id'))
		
    ss = merge_yearline_done(s1,s2,'personnel_id')
    for i in ss:
        ps = Personnel.objects.filter(personnel_id=i['personnel_id']).values('personnel_name')
        for j in ps:
            i.update({'personnel_name':j['personnel_name']})

    return make_annotate_sort_rsp(ss, True, True)

''' request
{
“start_time”:”2020-01-10 16:03:13”,
“end_time”:”2020-12-10 16:03:13”,
“personnel_id”:”2”,
“function”:”teamMemberStatistics”
}
'''
''' response
{
    "state": 0,
    "context": [
        {
            "leader_personnel_name": "童庆武",
            "personnel_id": "4",
            "personnel_name": "吴文浩",
            "item_money__sum": 3000,
            "item_money_fact__sum": 3100,
            "percent": "103.33"
        },
        {
            "leader_personnel_name": "童庆武",
            "personnel_id": "7",
            "personnel_name": "戚博",
            "item_money__sum": 6000,
            "item_money_fact__sum": 5500,
            "percent": "91.67"
        }
    ]
}
'''

def teamMemberStatistics(req):
    st = deal_time(req.get('start_time'))
    et = deal_time(req.get('end_time'))
    ty = req.get('personnel_id')
    if not st or not et or not ty:
        return True, make_err_rsp(u"params: start_time, end_time or personnel_id needed")

    yst = get_current_year() + '-01-01 00:00:00'
    yet = get_current_year() + '-12-31 23:59:59'
    s1 = VItemSortByArea.objects.values('personnel_leader_id', 'personnel_id').filter(item_flag=0,
         item_record_time__range=[yst,yet], personnel_leader_id=ty).annotate(Sum('item_money'), Sum('item_money_fact')).values(
        'personnel_id','personnel_name', item_money__sum = F('item_money__sum')) ## ,item_money_fact__sum = F('item_money_fact__sum')
    s2 = VItemSortByArea.objects.values('personnel_leader_id', 'personnel_id').filter(item_flag__in=(2,3),
     item_record_time__range=[st,et], personnel_leader_id=ty).annotate(Sum('item_money'), Sum('item_money_fact')).values(
    'personnel_id','personnel_name', item_money_fact__sum = F('item_money_fact__sum')) ## item_money__sum = F('item_money__sum'),
    ss = merge_yearline_done(s1,s2,'personnel_id')
    
    ps = Personnel.objects.filter(personnel_id=ty).values('personnel_name')
    [i.update({'leader_personnel_name': ps[0]['personnel_name']}) for i in ss if len(ps) >0]

    return make_annotate_sort_rsp(ss, True, True)

''' request
{
“start_time”:”2020-01-10 16:03:13”,
“end_time”:”2020-12-10 16:03:13”,
“personnel_id”:”2”,
“function”:”groupMemberAllStatistics”
}
'''

''' response
{
    "state": 0,
    "context": [
        {
            "personnel_id": "18672928722",
            "personnel_name": "吴文浩",
            "area_name": "湖南",
            "area_id": 2,
            "item_money__sum": "1287.59",
            "item_money_fact__sum": "654.88",
            "percent": "50.86"
        },
        {
            "personnel_id": "18672928722",
            "personnel_name": "吴文浩",
            "area_name": "福建",
            "area_id": 1,
            "item_money__sum": "1955.70",
            "item_money_fact__sum": "715.72",
            "percent": "36.59"
        },
        {
            "personnel_id": "18672928722",
            "personnel_name": "吴文浩",
            "area_name": "湖北",
            "area_id": 3,
            "item_money__sum": "3484.90",
            "item_money_fact__sum": "967.80",
            "percent": "27.77"
        }
    ]
}
'''

def groupMemberAllStatistics(req):
    st = deal_time(req.get('start_time'))
    et = deal_time(req.get('end_time'))
    ty = req.get('personnel_id')
    if not st or not et or not ty:
        return True, make_err_rsp(u"params: start_time, end_time or personnel_id needed")

    yst = get_current_year() + '-01-01 00:00:00'
    yet = get_current_year() + '-12-31 23:59:59'
    s1 = VItemSortByArea.objects.values('area_id').filter(item_flag=0,
        item_record_time__range=[yst, yet], personnel_id=ty).annotate(Sum('item_money'),
        Sum('item_money_fact')).values('personnel_id','personnel_name', 'area_name','area_id',
        item_money__sum = F('item_money__sum')).order_by('area_id') ##, item_money_fact__sum = F('item_money_fact__sum')
    s2 = VItemSortByArea.objects.values('area_id').filter(item_flag__in=(2,3),
        item_record_time__range=[st,et], personnel_id=ty).annotate(Sum('item_money'),
        Sum('item_money_fact')).values('personnel_id','personnel_name', 'area_name','area_id', ##item_money__sum = F('item_money__sum'),
        item_money_fact__sum = F('item_money_fact__sum')).order_by('area_id')
    ss = merge_yearline_done(s1, s2,'area_id')

    return make_annotate_sort_rsp(ss, True, True)

''' request
{
“start_time”:”2020-01-10 16:03:13”,
“end_time”:”2020-12-10 16:03:13”,
“function”:”mainProductStatistics”
}
'''

''' response
{
    "state": 0,
    "context": [
        {
            "product_type": "软件类",
            "item_money__sum": 16000,
            "item_money_fact__sum": 14500,
            "percent": "90.62"
        },
        {
            "product_type": "主设备",
            "item_money__sum": 25000,
            "item_money_fact__sum": 15600,
            "percent": "62.40"
        }
    ]
}
'''

def merge_yearline_done(s1, s2,key):
    ss = []
    fcount = 0
    for a in s1:
        a.update({'item_money_fact__sum': 0.0 })
        for j in s2:
            if j[key] == a[key]:
                a.update({'item_money_fact__sum': j['item_money_fact__sum']})
                fcount +=1
                break
        ss.append(a)

    if not (len(s1)>=len(s2) and len(s2) == fcount):
        for a in s2:
            fg = False
            a.update({'item_money__sum': 0.0})
            for j in s1:
                if j[key] == a[key]:
                    fg = True
                    break
            if not fg:
                ss.append(a)

    return ss

''' request
{
“start_time”:”2020-01-10 16:03:13”,
“end_time”:”2020-12-10 16:03:13”,
“personnel_id”:”2”,
“product_id”:”1”,
“function”:”groupMemberProductStatistics”
}
'''

''' response
{
    "state": 0,
    "context": [
        {
            "personnel_id": "18672928722",
            "personnel_name": "吴文浩",
            "area_id": 3,
            "area_name": "湖北",
            "product_id": 1,
            "item_type": 0,
            "item_flag": 0,
            "item_id__count": 6,
            "item_money__sum": "1782.00",
            "item_money_fact__sum": "0.00",
            "product_name": "维保",
            "name_comments": "",
            "percent": "0.00"
        }
    ]
}
'''

def groupMemberProductStatistics(req):
    st = deal_time(req.get('start_time'))
    et = deal_time(req.get('end_time'))
    ty = req.get('personnel_id')
    id = req.get('product_id')
    if not st or not et or not ty or not id:
        return True, make_err_rsp(u"params: start_time, end_time,product_id or personnel_id needed")

    yst = get_current_year() + '-01-01 00:00:00'
    yet = get_current_year() + '-12-31 23:59:59'
    s1 = VItemSortByArea.objects.values('area_id','item_type').filter(item_record_time__range=[yst,yet],
         personnel_id=ty,product_id=id,item_flag=0).annotate(Count('item_id'),Sum('item_money'),Sum('item_money_fact')
         ).values('personnel_id','personnel_name', 'area_id','area_name', 'product_id','item_type','item_flag',
         item_money__sum = F('item_money__sum'), ##item_money_fact__sum = F('item_money_fact__sum'),
         item_id__count = F('item_id__count'))
    s2 = VItemSortByArea.objects.values('area_id', 'item_type').filter(item_record_time__range=[st,et],
         personnel_id=ty, product_id=id,item_flag__in=(2,3)).annotate(Count('item_id'),Sum('item_money'),Sum('item_money_fact')
         ).values('personnel_id', 'personnel_name', 'area_id', 'area_name', 'product_id', 'item_type', ##item_money__sum=F('item_money__sum'),
         item_money_fact__sum=F('item_money_fact__sum'),
         item_id__count=F('item_id__count')) ##, 'item_flag'

    ps = Product.objects.filter(product_id=id).values('product_id','product_name','name_comments')
    # [i.update(ps[0]) for i in s1 if len(ps) > 0]
    # [i.update(ps[0]) for i in s2 if len(ps) > 0]
    for i in s1:
        i.update({'item_money_fact__sum':0.0 })
        if len(ps) > 0:
            i.update(ps[0])
    for i in s2:
        i.update({'item_money__sum':0.0 })
        i.update({'item_flag': 1 })
        if len(ps) > 0:
            i.update(ps[0])
    # merge
    ss = chain(s1,s2)

    return make_chainset_sort_rsp(ss,False,False)

def get_current_year(s=''):
    if s:
        return s[0:4]

    return time.strftime('%Y',time.localtime(time.time()))

''' request
{
“time_slice”:[
{“start_time”:”2020-01-01 00:00:00”,
 “end_time”:”2020-03-31 23:59:59”, 
 “flag”:”2019-第一季度”},
{“start_time”:”2020-04-01 00:00:00”,
 “end_time”:”2020-06-30 23:59:59”,
  “flag”:”2020-第二季度”}],
“product_id_list”:[1,2,3],
“function”:”compare_by_area_all”
}
'''

''' response
{
    "state": 0,
    "context": [
        {
            "product_id": 1,
            "product_name": "维保",
            "name_comments": "",
            "detail": [
                {
                    "flag": "2019-第一季度",
                    "item_money__sum": "22937.53",
                    "item_money_fact__sum": "2581.10",
                    "percent": "11.25"
                },
                {
                    "flag": "2020-第二季度",
                    "item_money__sum": "22937.53",
                    "item_money_fact__sum": "8579.12",
                    "percent": "37.40"
                },
                {
                    "flag": "2020-第san季度",
                    "item_money__sum": "22937.53",
                    "item_money_fact__sum": "1258.61",
                    "percent": "5.48"
                }
            ]
        }
    ]
}
'''

r ={
"flag": "",
"item_money__sum": 0.0,
"item_money_fact__sum": 0.0,
"percent": 0.0 }
def compare_by_area_all(req): #区域比对：总计
    ts = req.get('time_slice')
    pl = req.get('product_id_list')
    if not ts or not pl :
        return True, make_err_rsp(u"params: time_slice or product_id_list needed")
    ss = do_compare_query(ts,pl)

    return make_compare_rsp(ss )

''' request
{
“time_slice”:[
{“start_time”:”2020-01-01 00:00:00”,
 “end_time”:”2020-03-31 23:59:59”,
  “flag”:”2019-第一季度”},
  
{“start_time”:”2020-04-01 00:00:00”,
 “end_time”:”2020-06-30 23:59:59”,
  “flag”:”2020-第二季度”}],
  
“product_id_list”:[1,2,3],
“area_id”:”2”,
“function”:”compare_by_area_id”
}
'''

''' response
{
    "state": 0,
    "context": [
        {
            "product_id": 1,
            "product_name": "维保",
            "name_comments": "",
            "detail": [
                {
                    "flag": "2019-第一季度",
                    "item_money__sum": "589.00",
                    "item_money_fact__sum": "0.00",
                    "percent": "0.00"
                },
                {
                    "flag": "2020-第二季度",
                    "item_money__sum": "589.00",
                    "item_money_fact__sum": "158.16",
                    "percent": "26.85"
                },
                {
                    "flag": "2020-第san季度",
                    "item_money__sum": "589.00",
                    "item_money_fact__sum": "50.33",
                    "percent": "8.54"
                }
            ]
        }
    ]
}
'''

def compare_by_area_id(req):  #区域比对：区域id
    ts = req.get('time_slice')
    pl = req.get('product_id_list')
    id = req.get('area_id')
    if not ts or not pl or not id :
        return True, make_err_rsp(u"params: time_slice,area_id or product_id_list needed")

    ss = do_compare_query(ts,pl,id)
    return make_compare_rsp(ss)

def do_compare_query(ts,pl,id=''):
    ss = []
    ps = Product.objects.filter(product_id__in=pl).values('product_id', 'product_name', 'name_comments').order_by('product_id')
    for j in ps:
        j.update({'detail': []})
        ss.append(j)
    for i in ts:
        st, et = i['start_time'], i['end_time']
        yst = get_current_year(st) + '-01-01 00:00:00'
        yet = get_current_year(st) + '-12-31 23:59:59'
        if id :
            s1 = Item.objects.values('product_id').filter(area_id=id, item_record_time__range=[yst, yet],product_id__in=pl,
                 item_flag=0).annotate(Sum('item_money')).values('product_id', item_money__sum=F(
                'item_money__sum')).order_by('product_id')
            s2 = Item.objects.values('product_id').filter(area_id=id, item_record_time__range=[st, et],product_id__in=pl,
                 item_flag__in=(2, 3)).annotate(Sum('item_money_fact')).values(
                'product_id', item_money_fact__sum=F('item_money_fact__sum')).order_by('product_id')
        else:
            s1 = Item.objects.values('product_id').filter(item_record_time__range=[yst, yet], product_id__in=pl,
                 item_flag=0).annotate(Sum('item_money')).values('product_id',
                 item_money__sum=F('item_money__sum')).order_by('product_id')
            s2 = Item.objects.values('product_id').filter(item_record_time__range=[st, et], product_id__in=pl,
                 item_flag__in=(2, 3)).annotate(Sum('item_money_fact')).values(
                'product_id', item_money_fact__sum=F('item_money_fact__sum')).order_by('product_id')

        for j in ss:
            rt = copy.deepcopy(r)
            rt.update({'flag': i['flag']})
            j['detail'].append(rt)
            for a in s1:
                if j['product_id'] == a['product_id']:
                    rt.update({'item_money__sum': a['item_money__sum']})
                    break
            for a in s2:
                if j['product_id'] == a['product_id']:
                    rt.update({'item_money_fact__sum': a['item_money_fact__sum']})
                    break

    return ss

''' request
{
“product_id”:”2”,
“function”:”productByproductid”
}
'''
def productByproductid(req): 
    id = req.get('product_id')
    if not id :
        return True, make_err_rsp(u"params: product_id needed")

    ss = Product.objects.filter(product_id=id).all()

    return make_succeed_rsp(ss)

''' request
{
“product_name”:”网”,
“function”:”productByproductName”
}
'''
def productByproductName(req): 
    id = req.get('product_name')
    if not id :
        return True, make_err_rsp(u"params: product_name needed")

    # ss = Product.objects.filter(product_name=id).all()
    ss = Product.objects.filter(product_name__icontains=id).all()

    return make_succeed_rsp(ss)

''' request
{
“function”:”productList”
}
'''
def productList(req): 
    ss = Product.objects.filter().all()

    return make_succeed_rsp(ss)

''' request
{
“product_id”:1,
“function”:”productDuty”
}
'''
def productDuty(req): 
    id = req.get('product_id')
    if not id :
        return True, make_err_rsp(u"params: product_id needed")

    p = Product.objects.filter(product_id=id).first()
    if p:
        ss = Personnel.objects.filter(personnel_id=p.personnel_id ).all()

        return make_succeed_rsp(ss)

    return False, {}

''' request
{
“function”:”allProductDuty”
}
'''
def allProductDuty(req): 
    ss = Product.objects.all().values('product_id','product_name','name_comments','personnel_id').order_by('product_id')
    pid = [i['personnel_id'] for i in ss]
    p = Personnel.objects.filter(personnel_id__in=pid).values('personnel_id', 'personnel_name', 'personnel_leader_id')
    [ i.update(j) for i in ss for j in p if i['personnel_id'] == j['personnel_id'] ]

    return make_annotate_rsp(ss, True)

''' request
{
“item_id”:”8a988f7f4a8b72312fd48740ca823632”,
“function”:”itemByitemid”
}
'''
def itemByitemid(req): 
    id = req.get('item_id')
    if not id :
        return True, make_err_rsp(u"params: item_id needed")

    ss = Item.objects.filter(item_id=id).all()

    return make_succeed_rsp(ss)

''' request
{
“item_name”:”中邮建技术有限公司培训服务合同”,
“function”:”itemByitemName”
}
'''
def itemByitemName(req): 
    id = req.get('item_name')
    if not id :
        return True, make_err_rsp(u"params: item_name needed")

    ss = Item.objects.filter(item_name__icontains=id).all()

    return make_succeed_rsp(ss)

''' request
{
“function”:”itemList”
}
'''
def itemList(req): 
    ss = Item.objects.filter().all()

    return make_succeed_rsp(ss)

''' request
{
“personnel_id”:”2”,
“function”:”personnelByPersonnelid”
}
'''

def personnelBypersonnelid(req): 
    id = req.get('personnel_id')
    if not id :
        return True, make_err_rsp(u"params: personnel_id needed")
    ss = Personnel.objects.filter(personnel_id=id).all()
    return make_succeed_rsp(ss)

''' request
{
“personnel_name”:”吴文浩”,
“function”:”personnelByPersonnelid”
}
'''
def personnelByName(req): 
    id = req.get('personnel_name')
    if not id :
        return True, make_err_rsp(u"params: personnel_name needed")

    ss = Personnel.objects.filter(personnel_name__icontains=id).all()

    return make_succeed_rsp(ss)

''' request
{
“function”:”personnelList”
}
'''
def personnelList(req): 
    ss = Personnel.objects.filter().all()

    return make_succeed_rsp(ss)

''' request
{
“character_id”:”2”,
“function”:”personnelListByCharaterid”
}
'''
def personnelListByCharaterid(req):
    id = req.get('character_id')
    if not id :
        return True, make_err_rsp(u"params: character_id needed")

    ss = PersonnelCharacter.objects.values('character_id').filter(character_id=id).annotate(personnel_id_sum=Concat('personnel_id'))
    sp = Personnel.objects.filter(personnel_id__in=ss[0]['personnel_id_sum'].split(',')).all() if len(ss)>0 else []

    return make_succeed_rsp(sp)

''' request
{
“area_id”:”2”,
“function”:”areaByAreaid”
}
'''

def areaByAreaid(req):
    id = req.get('area_id')
    if not id :
        return True, make_err_rsp(u"params: area_id needed")

    ss = Area.objects.filter(area_id=id).all()

    return make_succeed_rsp(ss)

''' request
{
“area_name”:”湖南”,
“function”:”areaByAreaName”
}
'''

def areaByareaName(req): 
    id = req.get('area_name')
    if not id :
        return True, make_err_rsp(u"params: area_name needed")

    ss = Area.objects.filter(area_name__icontains=id).all()

    return make_succeed_rsp(ss)

''' request
{
“function”:”areaList”
}
'''

def areaList(req): 
    ss = Area.objects.filter().all()

    return make_succeed_rsp(ss)

# def areaLeaderlList(req):
#     ss = Area.objects.all().values('personnel_id','area_id','area_name')
#     return make_annotate_rsp(ss)

''' request
{
“personnel_id”:2,
“function”:”leader”
}
'''

def leader(req): 
    id = req.get('personnel_id')
    if not id :
        return True, make_err_rsp(u"params: personnel_id needed")

    sql = 'SELECT a.* FROM personnel a INNER JOIN personnel b ON \
           a.personnel_id = b.personnel_leader_id WHERE b.personnel_id = ' + str(id)
    ss = Personnel.objects.raw(sql)

    db_ret, ret_json = make_succeed_rsp(ss)
    
    if len(ret_json['context']) == 0:
        db_ret = False
        ss = Personnel.objects.filter(personnel_id=id).all()
        if ss.exists():
            for varl in ss:
                if varl.personnel_leader_id == "":
                    db_ret = True
                    ret = 'Big boss has no leader'
                    ret_json['context'].append(ret)
                    break

    return db_ret, ret_json

''' request
{
“character_id”:”2”,
“function”:”characterBycharacterid”
}
'''

def characterBycharacterid(req): 
    id = req.get('character_id')
    if not id :
        return True, make_err_rsp(u"params: character_id needed")

    ss = Character.objects.filter(character_id=id).all()
    return make_succeed_rsp(ss)

''' request
{
“character_name”:”普通员工”,
“function”:”characterBycharacterName”
}
'''

def characterBycharacterName(req): 
    id = req.get('character_name')
    if not id :
        return True, make_err_rsp(u"params: character_name needed")

    ss = Character.objects.filter(character_name__icontains=id).all()
    return make_succeed_rsp(ss)


''' request
{
“function”:”characterList”
}
'''

def characterList(req): 
    ss = Character.objects.filter().all()

    return make_succeed_rsp(ss)

##http请求的入口函数，Django的URL中配置
def query(request):
    try :
        fun = ''
        s_time = time.time()
        if request.method == 'POST':
            db_ret = False
            ret_json = {'state': 0, 'context': []}
            req = {}
            # return JsonResponse(ret_json, content_type="application/json", safe=False) ##小程序审核时打开

            bLogin, stateCode = tokenCheck(request, ret_json) #登陆权限校验
            if not bLogin:
                write_debug(ret_json)
                return JsonResponse(ret_json, content_type="application/json", safe=False, status=stateCode)

            ret, req = check_body(request)
            if not ret:
                return JsonResponse(req, content_type="application/json", safe=False)

            fun = req.get('function')
            if not fun:
                db_ret = True
                ret_json = make_err_rsp(u"参数: function为必选项")
            elif fun in fun_list:
                f = globals()[fun]
                db_ret, ret_json = f(req)
            else:
                db_ret = True
                ret_json = make_err_rsp(u"未知的请求function: " + fun )

            #no data
            if not db_ret :
                ret_json = make_err_rsp(u"无记录" )
        else :
            ret_json = make_err_rsp(u"请使用POST方法." )
        write_debug(fun + u": cost: %ss" % str('%f' % (time.time() - s_time)) )
        write_debug(ret_json)
    except Exception as e:
        log_debug.logger.debug(e, exc_info=1)
        ret_json = make_err_rsp(u"系统异常，请查询query.log了解详情.", str(e))
        write_debug(ret_json)

    return JsonResponse(ret_json, content_type="application/json", safe=False)

## 日志下载，特殊处理，不作为对外接口
def download_log(request):
    try:
        ty = request.GET.get('type')
        if ty == 'modify':
            file = "modify.log"
        elif ty == 'delete':
            file = "Delete.log"
        elif ty == 'load':
            file = "Load.log"
        else:
            file = "query.log"
        file_path = './' + file

        st = request.GET.get('num')
        num = 0
        if st and st > '0':
            num = int(st)
            response = StreamingHttpResponse(read_file_ex(file_path, num))
        else:
            response = StreamingHttpResponse(read_file(file_path))
        response["Content-Type"] = "application/octet-stream"
        response["Content-Disposition"] = 'attachment; filename={0}'.format(file)
        response["Access-Control-Expose-Headers"] = "Content-Disposition"  # 为了使前端获取到Content-Disposition属性

        return response
    except Exception as e:
        log_debug.logger.debug(e, exc_info=1)
        ret_json = make_err_rsp(u"系统异常，请查询query.log了解详情.", str(e))
        write_debug(ret_json)

    return JsonResponse(ret_json, content_type="application/json", safe=False)


def read_file(file_name, chunk_size=512):
    with open(file_name, "rb") as f:
        while True:
            c = f.read(chunk_size)
            if c:
                yield c
            else:
                break

def read_file_ex(file_name, num):
    flag = False
    with open(file_name, 'rb') as f:
        while True:
            if not flag:
                flag = True
                lines = f.readlines()
                l = len(lines)
                if l <= 0:
                    break
                i = 0
                j = l - num - 1
            if l <= num:
                yield lines[i]
                i += 1
            else:
                if j < l - 1:
                    yield lines[j]
                    j += 1
                else:
                    break


#启动日志
write_debug(u"-----------query server started.")



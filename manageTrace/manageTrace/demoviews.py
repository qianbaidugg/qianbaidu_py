

from django.http import HttpResponse
from django.http import JsonResponse
import  json

def index(request):

    if request.method == 'POST':

        jsoninfo = json.loads(request.body)
        personid = jsoninfo.get('personnel_id')
        fun = jsoninfo.get('function')  # yearResult

        varResult = {}
        varResult['personnel_id'] = personid
        varResult['function'] = fun
        json_str = json.dumps(varResult)  # json.dumps(dict_, indent=2, sort_keys=True, ensure_ascii=False)
        return JsonResponse(json_str, content_type="application/json", safe=False)

    elif request.method == 'GET':
        sid = request.GET.get('id')
        subject1 = request.GET.get('subject')
        print('GET', sid, subject1)

        jsondata = {'foo111': 'bar111'}
        return JsonResponse(jsondata, content_type="application/json")

    else :
        return HttpResponse("Hello, world else2222")


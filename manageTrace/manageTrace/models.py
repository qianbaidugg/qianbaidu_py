# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Area(models.Model):
    id = models.SmallAutoField(primary_key=True)
    area_id = models.SmallIntegerField(unique=True)
    area_name = models.CharField(max_length=32)
    personnel = models.ForeignKey('Personnel', models.DO_NOTHING)
    reserved1 = models.CharField(max_length=32, blank=True, null=True)
    reserved2 = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'area'


class Character(models.Model):
    id = models.SmallAutoField(primary_key=True)
    character_id = models.SmallIntegerField(unique=True)
    character_name = models.CharField(max_length=32)
    permission_content = models.CharField(max_length=32)
    reserved1 = models.CharField(max_length=32, blank=True, null=True)
    reserved2 = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'character'


class Item(models.Model):
    item_id = models.CharField(unique=True, max_length=64)
    item_name = models.CharField(max_length=255)
    item_money = models.FloatField()
    item_money_fact = models.FloatField()
    item_type = models.SmallIntegerField()
    item_state = models.SmallIntegerField()
    item_frame = models.SmallIntegerField()
    item_frame_money = models.FloatField()
    item_flag = models.SmallIntegerField()
    item_modify_time = models.DateTimeField()
    item_record_time = models.DateTimeField()
    area = models.ForeignKey(Area, models.DO_NOTHING)
    product = models.ForeignKey('Product', models.DO_NOTHING)
    personnel = models.ForeignKey('Personnel', models.DO_NOTHING)
    reserved1 = models.CharField(max_length=32, blank=True, null=True)
    reserved2 = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'item'


class ItemHis(models.Model):
    item_id = models.CharField(max_length=64)
    item_name = models.CharField(max_length=255)
    item_money = models.FloatField()
    item_money_fact = models.FloatField()
    item_type = models.SmallIntegerField()
    item_state = models.SmallIntegerField()
    item_frame = models.SmallIntegerField()
    item_frame_money = models.FloatField()
    item_flag = models.SmallIntegerField()
    item_modify_time = models.DateTimeField()
    item_record_time = models.DateTimeField()
    area = models.ForeignKey(Area, models.DO_NOTHING)
    product = models.ForeignKey('Product', models.DO_NOTHING)
    personnel = models.ForeignKey('Personnel', models.DO_NOTHING)
    area_id_old = models.SmallIntegerField()
    product_id_old = models.SmallIntegerField()
    personnel_id_old = models.CharField(max_length=32)
    item_item_id = models.CharField(max_length=64)

    item_money_fact_old = models.FloatField()
    item_state_old = models.SmallIntegerField()
    item_flag_old = models.SmallIntegerField()
    reserved1_old = models.CharField(max_length=32, blank=True, null=True)

    action = models.SmallIntegerField()
    reserved1 = models.CharField(max_length=32, blank=True, null=True)
    reserved2 = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'item_his'


class Login(models.Model):
    token_str = models.CharField(max_length=64)
    token_modify_time = models.DateTimeField()
    reserved1 = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'login'


class Personnel(models.Model):
    id = models.SmallAutoField(primary_key=True)
    personnel_id = models.CharField(unique=True, max_length=32)
    personnel_name = models.CharField(max_length=32)
    personnel_leader_id = models.CharField(max_length=32)
    reserved1 = models.CharField(max_length=32, blank=True, null=True)
    reserved2 = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'personnel'


class PersonnelCharacter(models.Model):
    id = models.SmallAutoField(primary_key=True)
    character = models.ForeignKey(Character, models.DO_NOTHING)
    personnel = models.ForeignKey(Personnel, models.DO_NOTHING)
    reserved1 = models.CharField(max_length=32, blank=True, null=True)
    reserved2 = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'personnel_character'


class Product(models.Model):
    id = models.SmallAutoField(primary_key=True)
    product_id = models.SmallIntegerField(unique=True)
    product_name = models.CharField(max_length=32)
    product_type = models.CharField(max_length=3)
    name_comments = models.CharField(max_length=32)
    personnel = models.ForeignKey(Personnel, models.DO_NOTHING)
    q1 = models.FloatField(db_column='Q1')  # Field name made lowercase.
    q2 = models.FloatField(db_column='Q2')  # Field name made lowercase.
    q3 = models.FloatField(db_column='Q3')  # Field name made lowercase.
    q4 = models.FloatField(db_column='Q4')  # Field name made lowercase.
    reserved1 = models.CharField(max_length=32, blank=True, null=True)
    reserved2 = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'product'


class Weight(models.Model):
    id = models.SmallAutoField(primary_key=True)
    area_q1 = models.FloatField(db_column='area_Q1')  # Field name made lowercase.
    area_q2 = models.FloatField(db_column='area_Q2')  # Field name made lowercase.
    area_q3 = models.FloatField(db_column='area_Q3')  # Field name made lowercase.
    area_q4 = models.FloatField(db_column='area_Q4')  # Field name made lowercase.
    area_inc = models.FloatField()
    area_sto = models.FloatField()
    product_dev_inc = models.FloatField()
    product_soft_inc = models.FloatField()
    product_dev_sto = models.FloatField()
    product_soft_sto = models.FloatField()

    class Meta:
        managed = False
        db_table = 'weight'


class VItemSortByArea(models.Model):
    item_id = models.CharField(max_length=64,primary_key=True)
    item_name = models.CharField(max_length=255)
    item_money = models.FloatField()
    item_money_fact = models.FloatField()
    item_type = models.SmallIntegerField()
    item_state = models.SmallIntegerField()
    item_frame = models.SmallIntegerField()
    item_frame_money = models.FloatField()
    item_flag = models.SmallIntegerField()
    item_modify_time = models.DateTimeField()
    item_record_time = models.DateTimeField()
    area_id = models.SmallIntegerField()
    area_name = models.CharField(max_length=32)
    product_id = models.SmallIntegerField()
    personnel_id = models.CharField(max_length=32)
    personnel_name = models.CharField(max_length=32)
    personnel_leader_id = models.CharField(max_length=32)

    class Meta:
        managed = False  # Created from a view. Don't remove.
        db_table = 'v_item_sort_by_area'


class VItemSortByProduct(models.Model):
    item_id = models.CharField(max_length=64,primary_key=True)
    item_name = models.CharField(max_length=255)
    item_money = models.FloatField()
    item_money_fact = models.FloatField()
    item_type = models.SmallIntegerField()
    item_state = models.SmallIntegerField()
    item_frame = models.SmallIntegerField()
    item_frame_money = models.FloatField()
    item_flag = models.SmallIntegerField()
    item_modify_time = models.DateTimeField()
    item_record_time = models.DateTimeField()
    area_id = models.SmallIntegerField()
    product_id = models.SmallIntegerField()
    product_name = models.CharField(max_length=32)
    name_comments = models.CharField(max_length=32)
    product_type = models.CharField(max_length=3)
    personnel_id = models.CharField(max_length=32)
    personnel_name = models.CharField(max_length=32)
    personnel_leader_id = models.CharField(max_length=32)

    class Meta:
        managed = False  # Created from a view. Don't remove.
        db_table = 'v_item_sort_by_product'


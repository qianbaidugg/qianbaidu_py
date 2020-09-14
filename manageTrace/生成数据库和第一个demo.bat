:python manage.py createsuperuser
:python manage.py help

rem https://blog.csdn.net/ZhangK9509/article/details/80280432
rem 创建项目：
django-admin startproject mysite

rem 生成数据库模型：
python manage.py startapp article

rem 同步数据库，生成迁移文件：
python manage.py makemigrations

rem 应用该迁移文件：
python manage.py migrate

rem 从数据库生成模块文件； ==》 migrate 可能出错；  => 加入app头文件里面；
python mysite/manage.py inspectdb > mysite/myapp/models.py

rem python3 manage.py shell

rem  python manage.py runserver  http://192.168.43.115:8000/

pause

#报错时，把版本号这段代码注释掉；
#if version < (1, 3, 13):
#    raise ImproperlyConfigured('mysqlclient 1.3.13 or newer is required; you have %s.' % Database.__version__)
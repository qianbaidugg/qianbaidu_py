:python manage.py createsuperuser
:python manage.py help

rem https://blog.csdn.net/ZhangK9509/article/details/80280432
rem ������Ŀ��
django-admin startproject mysite

rem �������ݿ�ģ�ͣ�
python manage.py startapp article

rem ͬ�����ݿ⣬����Ǩ���ļ���
python manage.py makemigrations

rem Ӧ�ø�Ǩ���ļ���
python manage.py migrate

rem �����ݿ�����ģ���ļ��� ==�� migrate ���ܳ���  => ����appͷ�ļ����棻
python mysite/manage.py inspectdb > mysite/myapp/models.py

rem python3 manage.py shell

rem  python manage.py runserver  http://192.168.43.115:8000/

pause

#����ʱ���Ѱ汾����δ���ע�͵���
#if version < (1, 3, 13):
#    raise ImproperlyConfigured('mysqlclient 1.3.13 or newer is required; you have %s.' % Database.__version__)
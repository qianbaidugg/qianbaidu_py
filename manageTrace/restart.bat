@echo off
if "%1" == "h" goto begin
	mshta vbscript:createobject("wscript.shell").run("%~nx0 h",0)(window.close)&&exit
:begin
::下面是你自己的代码

@echo off
@tasklist|find "python.exe"
@if %errorlevel%==0 taskkill.exe /IM python.exe /t /f
@ping 127.0.0.1>nul
rem @start 您程序的绝对路径\您的程序名
python ./manage.py runserver 0.0.0.0:8000

REM @echo on
REM echo "server started..."
@exit
REM pause
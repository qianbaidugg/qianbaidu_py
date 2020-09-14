@echo off
@tasklist|find "python.exe"
@if %errorlevel%==0 taskkill.exe /IM python.exe /t /f

pause
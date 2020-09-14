@echo off
set a=restart.bat
for /f "delims=" %%i in ('dir /b /s %a%') do (
reg add "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\windows\CurrentVersion\run" /v bat1.bat /t "reg_sz" /d %%i /f
)

pause
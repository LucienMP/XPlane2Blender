@echo off
rem Builds win.xpl with Visual Studio 2022. Usage: build.bat PATH\TO\XPSDK430\SDK
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
cd /d "%~dp0"
cl /nologo /O2 /LD /DIBM=1 /DXPLM200=1 /DXPLM210=1 /DXPLM300=1 /DXPLM301=1 /DXPLM303=1 /DXPLM400=1 /DXPLM410=1 /DXPLM420=1 /DXPLM430=1 /I"%~1\CHeaders\XPLM" xp2b_instancing_test.c /link "%~1\Libraries\Win\XPLM_64.lib" /OUT:win.xpl

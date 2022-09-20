@echo off
set PLUGIN_ZIP=Baen.zip

cd ..

echo Building plugin zip: %PLUGIN_ZIP%
python ..\common\build.py "%PLUGIN_ZIP%"
if %ERRORLEVEL% NEQ 0 GOTO ExitPoint:

echo Installing plugin
if defined CALIBRE_DIRECTORY (
    "%CALIBRE_DIRECTORY%\calibre-customize" -a "%PLUGIN_ZIP%"
) else (
    calibre-customize -a "%PLUGIN_ZIP%"
)

:ExitPoint
cd .build

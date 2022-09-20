@echo off
set PLUGIN_ZIP=Cover Url.zip

cd ..

echo Copying common files for zip
xcopy ..\common\common_*.py . /Y > nul

echo Building plugin zip: %PLUGIN_ZIP%
python ..\common\build.py "%PLUGIN_ZIP%"
if %ERRORLEVEL% NEQ 0 GOTO ExitPoint:

echo Deleting common files after zip
del common_*.py

echo Installing plugin
if defined CALIBRE_DIRECTORY (
    "%CALIBRE_DIRECTORY%\calibre-customize" -a "%PLUGIN_ZIP%"
) else (
    calibre-customize -a "%PLUGIN_ZIP%"
)

:ExitPoint
cd .build

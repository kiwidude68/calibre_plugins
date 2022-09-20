@echo off
set PLUGIN_ZIP=FictionDB.zip

cd ..\translations
set PYTHONIOENCODING=UTF-8
for %%f in (*.po) do (
    echo Compiling translation for: %%~nf
    if defined CALIBRE_DIRECTORY (
        "%CALIBRE_DIRECTORY%\calibre-debug.exe" -c "from calibre.translations.msgfmt import main; main()" %%~nf
    ) else (
        calibre-debug.exe -c "from calibre.translations.msgfmt import main; main()" %%~nf
    )
)
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

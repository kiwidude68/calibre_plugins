@echo off
cd ..
if exist "translations" (
    cd translations
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
) else (
    echo No translations subfolder found
)

echo Copying common files for zip
xcopy ..\common\common_*.py . /Y > nul

python ..\common\build.py
if %ERRORLEVEL% NEQ 0 GOTO ExitPoint:

echo Deleting common files after zip
del common_*.py

rem Determine the zip file that just got created
FOR /F "delims=" %%I IN ('DIR "*.zip" /A-D /B /O:D') DO SET "PLUGIN_ZIP=%%I"

echo Installing plugin "%PLUGIN_ZIP%" into calibre...
if defined CALIBRE_DIRECTORY (
    "%CALIBRE_DIRECTORY%\calibre-customize" -a "%PLUGIN_ZIP%"
) else (
    calibre-customize -a "%PLUGIN_ZIP%"
)
echo Build completed successfully

:ExitPoint
cd .build

@set PLUGIN_ZIP=Modify ePub.zip

@pushd
@cd ..\translations
@set PYTHONIOENCODING=UTF-8
@for %%f in (*.po) do (
    "C:\Program Files\Calibre2\calibre-debug.exe" -c "from calibre.translations.msgfmt import main; main()" %%~nf
)
@cd ..

@xcopy ..\common\common_*.py . /Y > nul
python ..\common\build.py "%PLUGIN_ZIP%"
@del common_*.py

calibre-customize -a "%PLUGIN_ZIP%"
@popd
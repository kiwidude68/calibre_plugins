@set PLUGIN_ZIP=Barnes Noble.zip

@pushd
@cd ..\translations
@set PYTHONIOENCODING=UTF-8
@for %%f in (*.po) do (
    "C:\Program Files\Calibre2\calibre-debug.exe" -c "from calibre.translations.msgfmt import main; main()" %%~nf
)
@cd ..

python ..\common\build.py "%PLUGIN_ZIP%"

calibre-customize -a "%PLUGIN_ZIP%"
@popd
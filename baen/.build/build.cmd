@set PLUGIN_ZIP=Baen.zip

@pushd
@cd ..

python ..\common\build.py "%PLUGIN_ZIP%"

calibre-customize -a "%PLUGIN_ZIP%"
@popd
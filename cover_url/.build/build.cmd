@set PLUGIN_ZIP=Cover Url.zip

@pushd
@cd ..

@xcopy ..\common\common_*.py . /Y > nul
python ..\common\build.py "%PLUGIN_ZIP%"
@del common_*.py

calibre-customize -a "%PLUGIN_ZIP%"
@popd
@pushd
@cd ..
python C:\Python310\Tools\i18n\pygettext.py -d fictiondb -p translations^
 config.py ..\common\common_*.py
@popd
@pushd
@cd ..
python C:\Python310\Tools\i18n\pygettext.py -d goodreads -p translations^
 config.py ..\common\common_*.py
@popd
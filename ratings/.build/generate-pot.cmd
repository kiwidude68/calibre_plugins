@pushd
@cd ..
python C:\Python310\Tools\i18n\pygettext.py -d ratings -p translations^
 action.py config.py jobs.py ..\common\common_*.py
@popd
@pushd
@cd ..
python C:\Python310\Tools\i18n\pygettext.py -d goodreads-sync -p translations^
 action.py config.py core.py dialogs.py ..\common\common_*.py
@popd
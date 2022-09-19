@pushd
@cd ..
python C:\Python310\Tools\i18n\pygettext.py -d extract-isbn -p translations^
 action.py config.py dialogs.py jobs.py ..\common\common_*.py
@popd
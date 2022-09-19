@pushd
@cd ..
python C:\Python310\Tools\i18n\pygettext.py -d generate-cover -p translations^
 action.py config.py dialogs.py ..\common\common_*.py
@popd
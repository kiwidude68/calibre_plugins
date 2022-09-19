@pushd
@cd ..
python C:\Python310\Tools\i18n\pygettext.py -d quality-check -p translations^
 action.py config.py dialogs.py ..\common\common_*.py^
 check_base.py check_covers.py check_epub.py check_fix.py check_metadata.py^
 check_mobi.py mobi6.py
@popd

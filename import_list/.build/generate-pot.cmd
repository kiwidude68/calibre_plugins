@pushd
@cd ..
python C:\Python310\Tools\i18n\pygettext.py -d import-list -p translations^
 action.py cmdline.py config.py ..\common\common_*.py^
 encodings.py models.py page_import.py page_persist.py page_resolve.py^
 tab_clipboard.py tab_common.py tab_csv.py tab_settings.py tab_webpage.py wizards.py
@popd
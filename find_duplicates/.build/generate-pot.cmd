@pushd
@cd ..
python C:\Python310\Tools\i18n\pygettext.py -d find-duplicates -p translations^
 action.py config.py book_algorithms.py dialogs.py ..\common\common_*.py^
 duplicates.py advanced\*.py advanced\gui\*.py
@popd
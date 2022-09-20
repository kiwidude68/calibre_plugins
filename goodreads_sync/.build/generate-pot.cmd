@echo off
cd ..

set PYGETTEXT=C:\Python310\Tools\i18n\pygettext.py
if defined PYGETTEXT_FOLDER (
    set PYGETTEXT=%PYGETTEXT_FOLDER%\pygettext.py
)

echo Regenerating translations .pot file
python %PYGETTEXT% -d goodreads-sync -p translations^
 action.py config.py core.py dialogs.py ..\common\common_*.py

set PYGETTEXT=
cd .build

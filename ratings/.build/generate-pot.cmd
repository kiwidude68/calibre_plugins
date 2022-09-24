@echo off
cd ..

set PYGETTEXT=C:\Python310\Tools\i18n\pygettext.py
if defined PYGETTEXT_DIRECTORY (
    set PYGETTEXT=%PYGETTEXT_DIRECTORY%\pygettext.py
)

echo Regenerating translations .pot file
python %PYGETTEXT% -d ratings -p translations^
 action.py config.py jobs.py ..\common\common_*.py

set PYGETTEXT=
cd .build

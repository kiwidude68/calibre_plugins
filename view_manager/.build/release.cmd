@echo off
call build.cmd

cd ..

python ..\common\release.py "%CALIBRE_GITHUB_TOKEN%"

cd .build

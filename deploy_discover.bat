@echo off
cd /d C:\home\node\.openclaw\workspace\skills\ad-radar
echo [1/3] Copying discover to www/discover...
if not exist "www\discover" mkdir "www\discover"
copy /Y "www\discover\index.html" "www\index_discover_backup.html" >nul
xcopy /Y /E "www\discover\*" "www\" >nul 2>&1
echo [2/3] Committing...
git add -A
git diff --cached --quiet
if %errorlevel% neq 0 (
    git commit -m "Deploy discover: AD Finder thematic search"
)
echo [3/3] Pushing...
git push origin master

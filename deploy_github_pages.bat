@echo off
cd /d C:\home\node\.openclaw\workspace\skills\ad-radar
echo [1/4] Running combined pipeline...
python combined_pipeline.py
if %errorlevel% neq 0 (
    echo ERROR: Pipeline failed
    exit /b 1
)

echo [2/4] Committing changes...
git add -A
git diff --cached --quiet
if %errorlevel% equ 0 (
    echo No changes to commit
) else (
    git commit -m "Auto-deploy %date% %time%"
    echo [3/4] Pushing to GitHub...
    git push origin master
    if %errorlevel% neq 0 (
        echo ERROR: Git push failed
        exit /b 1
    )
    echo [4/4] Done! GitHub Actions will deploy shortly.
)

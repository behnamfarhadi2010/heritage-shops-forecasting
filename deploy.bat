@echo off
REM Heritage Shops Forecasting - Quick Deploy Script (Windows)

echo ================================
echo Heritage Shops Deployment Helper
echo ================================
echo.

REM Check if git is initialized
if not exist ".git" (
    echo Initializing Git repository...
    git init
    echo Git initialized
) else (
    echo Git already initialized
)

REM Get GitHub username
set /p github_username="Enter your GitHub username: "

REM Get repository name
set /p repo_name="Enter repository name (default: heritage-shops-forecasting): "
if "%repo_name%"=="" set repo_name=heritage-shops-forecasting

echo.
echo Summary:
echo   Repository: https://github.com/%github_username%/%repo_name%
echo.
set /p confirm="Is this correct? (y/n): "

if /i not "%confirm%"=="y" (
    echo Cancelled
    exit /b
)

REM Add all files
echo.
echo Adding files to Git...
git add .

REM Commit
set /p commit_msg="Enter commit message (default: Initial commit): "
if "%commit_msg%"=="" set commit_msg=Initial commit - Heritage Shops forecasting system

git commit -m "%commit_msg%"
echo Files committed

REM Add remote (remove if exists)
git remote remove origin 2>nul
git remote add origin https://github.com/%github_username%/%repo_name%.git

REM Rename branch to main
git branch -M main

REM Push to GitHub
echo.
echo Pushing to GitHub...
git push -u origin main

if %errorlevel%==0 (
    echo.
    echo ================================
    echo Successfully pushed to GitHub!
    echo ================================
    echo.
    echo Your repository: https://github.com/%github_username%/%repo_name%
    echo.
    echo NEXT STEPS:
    echo 1. Go to: https://streamlit.io/cloud
    echo 2. Sign in with GitHub
    echo 3. Click 'New app'
    echo 4. Select your repository: %github_username%/%repo_name%
    echo 5. Main file: app.py
    echo 6. Click 'Deploy!'
    echo.
    echo Your app will be live at:
    echo https://%repo_name%.streamlit.app
) else (
    echo.
    echo Push failed. Common issues:
    echo   1. Repository doesn't exist on GitHub
    echo      Create it at: https://github.com/new
    echo   2. Authentication failed
    echo      Set up credentials or use GitHub Desktop
    echo.
    echo After fixing, run: git push -u origin main
)

pause

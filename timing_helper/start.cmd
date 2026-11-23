@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "dist\CookingTimingHelper-v8.exe" (
    start "" "dist\CookingTimingHelper-v8.exe"
    exit /b
)
if exist "dist\CookingTimingHelper-v7.exe" (
    start "" "dist\CookingTimingHelper-v7.exe"
    exit /b
)
if exist "dist\CookingTimingHelper-v6.exe" (
    start "" "dist\CookingTimingHelper-v6.exe"
    exit /b
)
if exist "dist\CookingTimingHelper-v5.exe" (
    start "" "dist\CookingTimingHelper-v5.exe"
    exit /b
)
if exist "dist\CookingTimingHelper-v4.exe" (
    start "" "dist\CookingTimingHelper-v4.exe"
    exit /b
)
if exist "dist\CookingTimingHelper-v3.exe" (
    start "" "dist\CookingTimingHelper-v3.exe"
    exit /b
)
if exist "dist\CookingTimingHelper.exe" (
    start "" "dist\CookingTimingHelper.exe"
    exit /b
)
python -c "import cv2, mss, numpy, PIL, dxcam" >nul 2>&1
if errorlevel 1 (
    python -m pip install -r requirements.txt
    if errorlevel 1 goto failed
)
python app.py
if errorlevel 1 goto failed
exit /b
:failed
echo 실행에 실패했습니다. 위 오류를 확인해주세요.
pause

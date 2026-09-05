@echo off
chcp 65001 >nul
title ZeusExAI / James

set "ZEUSEXAI_DIR=C:\Users\User\Documents\ZeusExAI"
set "ZEUSEXAI_APP=%ZEUSEXAI_DIR%\frontend\src-tauri\target\release\openjarvis-desktop.exe"
cd /d "%ZEUSEXAI_DIR%"

if not exist "%ZEUSEXAI_APP%" goto :missing_app

start "" /D "%ZEUSEXAI_DIR%\frontend\src-tauri\target\release" "%ZEUSEXAI_APP%"
exit /b 0

:missing_app
echo.
echo O executavel do ZeusExAI nao foi encontrado no build local.
pause
exit /b 1

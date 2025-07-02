@echo off
echo 📊 Twitch Miner Log Checker
echo ==========================

if "%1"=="live" goto live
if "%1"=="auth" goto auth
if "%1"=="status" goto status

:menu
echo Commands:
echo   check-logs.bat live    - Monitor live logs
echo   check-logs.bat auth    - Check authentication events  
echo   check-logs.bat status  - Check container status
echo.

:status
echo 🏥 Container status:
docker-compose ps
echo.
docker-compose ps | findstr "Up" >nul
if %errorlevel%==0 (
    echo ✅ Container is running
) else (
    echo ❌ Container is not running
)
goto end

:auth
echo 🔐 Authentication events:
echo ------------------------
echo Activation codes:
docker-compose logs twitch-miner 2>nul | findstr /i "enter this code"
echo.
echo Automation events:
docker-compose logs twitch-miner 2>nul | findstr /i "automated login"
echo.
echo Success events:
docker-compose logs twitch-miner 2>nul | findstr /i "login.*success authentication.*success"
echo.
echo Recent errors:
docker-compose logs twitch-miner 2>nul | findstr /i "error failed exception" | more +5
goto end

:live
echo 📡 Live logs (Ctrl+C to stop):
docker-compose logs -f twitch-miner
goto end

:end
if "%1"=="" pause
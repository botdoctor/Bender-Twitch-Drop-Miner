@echo off
echo ⚡ Twitch Miner Docker Test (Windows)
echo ========================================

echo 🧹 Cleaning up existing containers...
docker-compose down >nul 2>&1
docker rm -f twitch-miner >nul 2>&1

echo 📁 Creating directories...
if not exist logs mkdir logs
if not exist cookies mkdir cookies

echo 🔧 Configuration:
echo   Username: treaclefamousn6g
echo   Streamer file: ruststreamers.txt
echo   Log directory: .\logs
echo   Cookie directory: .\cookies

echo.
echo 🚀 Starting Docker build and run...
echo    This will take 5-10 minutes for first build (Chrome installation)
echo    Watch for these events:
echo    - "enter this code: XXXXXXXX" (activation code)
echo    - "Created activation_code.txt" (automation trigger)
echo    - "Starting automated login" (selenium start)
echo    - "Login successful" (success!)
echo.
echo Press Ctrl+C to stop when done
echo.

REM Set environment variables
set TWITCH_USERNAME=treaclefamousn6g
set STREAMER_FILE=ruststreamers.txt

REM Run docker-compose with logging
docker-compose up --build

echo.
echo 🏁 Test completed!
echo.
echo To check logs again: docker-compose logs twitch-miner
echo To stop container: docker-compose down
pause
@echo off
REM Docker management script for Telescope Correlator (Windows)

cd /d "%~dp0"

if "%1"=="cli" goto cli
if "%1"=="build" goto build
if "%1"=="test" goto test
if "%1"=="run" goto run
if "%1"=="pull-run" goto pull-run
if "%1"=="dev" goto dev
if "%1"=="clean" goto clean
goto help

:cli
echo [INFO] Starting interactive correlator CLI...
docker compose up cli
goto end

:build
echo [INFO] Building Docker image...
docker compose build
echo [SUCCESS] Docker image built successfully
goto end

:test
echo [INFO] Running tests...
docker compose run --rm test
echo [SUCCESS] Tests completed
goto end

:run
echo [INFO] Running correlator...
docker compose run --rm correlator python -m correlator %2 %3 %4 %5 %6 %7 %8 %9
goto end

:pull-run
echo [INFO] Pulling latest published image...
docker pull ghcr.io/francois0203/telescope-correlator:latest
echo [SUCCESS] Latest image pulled successfully
echo [INFO] Running correlator with latest image...
docker run --rm -v "%~dp0dev_workspace\outputs:/app/outputs" ghcr.io/francois0203/telescope-correlator:latest python -m correlator %2 %3 %4 %5 %6 %7 %8 %9
goto end

:dev
echo [INFO] Starting development shell...
docker compose run --rm dev
goto end

:clean
echo [INFO] Cleaning up Docker resources...
docker compose down -v --rmi local 2>nul
docker system prune -f >nul 2>&1
echo [SUCCESS] Cleanup completed
goto end

:help
echo Telescope Correlator Docker Management Script
echo.
echo Usage: %0 ^<command^> [options]
echo.
echo Commands:
echo   cli       Start interactive correlator CLI (persistent)
echo   build     Build the Docker image
echo   test      Run the test suite
echo   run       Run the correlator (pass correlator args after command)
echo   pull-run  Pull latest published image and run correlator
echo   dev       Start development shell
echo   clean     Clean up Docker resources
echo   help      Show this help message
echo.
echo Examples:
echo   %0 build
echo   %0 test
echo   %0 run --n-ants 4 --n-channels 128 --sim-duration 1.0 --output-dir /app/outputs
echo   %0 dev
echo   %0 clean
goto end

:end
@echo off
REM Telescope Correlator - Production-Ready CLI
REM Usage: correlator [MODE] [command] [options]
REM Modes: dev (development/simulation) or prod (production/real telescopes)

SET IMAGE_NAME=telescope-correlator

REM Check if Docker is available
docker --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Docker is not installed or not in PATH
    echo Please install Docker Desktop: https://www.docker.com/products/docker-desktop
    exit /b 1
)

REM Get the mode (dev/prod) or command
SET MODE=%1
IF "%MODE%"=="" (
    echo Telescope Correlator - FX Architecture
    echo.
    echo Usage: correlator [MODE] [OPTIONS]
    echo.
    echo Modes:
    echo   dev          Development mode - simulations, testing, learning
    echo   prod         Production mode - real telescope data processing
    echo   build        Build Docker image
    echo   test         Run tests
    echo.
    echo Examples:
    echo   correlator dev           Start interactive development CLI
    echo   correlator prod          Start interactive production CLI
    echo   correlator dev run --n-ants 8
    echo   correlator prod stream --source tcp://host:port
    echo   correlator build         Build the container
    echo   correlator test          Run tests
    echo.
    exit /b 0
)

REM Shift to get remaining arguments
SHIFT

REM Handle different modes and commands
IF "%MODE%"=="build" (
    echo Cleaning up old Docker images...
    docker image rm %IMAGE_NAME% >nul 2>&1
    docker image prune -f >nul 2>&1
    echo.
    echo Building Telescope Correlator...
    docker build -f app/Dockerfile -t %IMAGE_NAME% .
    IF %ERRORLEVEL% EQU 0 (
        echo.
        echo ✓ Build successful!
        echo Run 'correlator dev' or 'correlator prod' to start
    )
    exit /b %ERRORLEVEL%
)

IF "%MODE%"=="dev" (
    REM Check if image exists, build if not
    docker image inspect %IMAGE_NAME% >nul 2>&1
    IF %ERRORLEVEL% NEQ 0 (
        echo Image not found. Building...
        docker build -f app/Dockerfile -t %IMAGE_NAME% . -q
    )
    
    echo Starting Development Mode CLI...
    echo.
    docker run -it --rm -v "%CD%\workspace:/workspace" %IMAGE_NAME% python -m correlator dev %1 %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)

IF "%MODE%"=="prod" (
    REM Check if image exists, build if not
    docker image inspect %IMAGE_NAME% >nul 2>&1
    IF %ERRORLEVEL% NEQ 0 (
        echo Image not found. Building...
        docker build -f app/Dockerfile -t %IMAGE_NAME% . -q
    )
    
    echo Starting Production Mode CLI...
    echo.
    docker run -it --rm --network host -v "%CD%\workspace:/workspace" %IMAGE_NAME% python -m correlator prod %1 %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)



IF "%MODE%"=="test" (
    REM Check if image exists, build if not
    docker image inspect %IMAGE_NAME% >nul 2>&1
    IF %ERRORLEVEL% NEQ 0 (
        echo Image not found. Building...
        docker build -f app/Dockerfile -t %IMAGE_NAME% . -q
    )
    
    echo Running tests...
    docker run --rm -v "%CD%:/workspace" -e PYTHONPATH=/workspace/app/src:/usr/local/lib/python3.11/site-packages -w /workspace %IMAGE_NAME% pytest tests_harness/ -v
    exit /b %ERRORLEVEL%
)

IF "%MODE%"=="help" (
    goto :show_help
)

IF "%MODE%"=="-h" (
    goto :show_help
)

IF "%MODE%"=="--help" (
    goto :show_help
)

REM Unknown mode/command
echo Unknown mode: %MODE%
echo.
goto :show_help

:show_help
echo Telescope Correlator - FX Architecture
echo.
echo Usage: correlator [MODE] [OPTIONS]
echo.
echo Modes:
echo   dev          Development mode - simulations, testing, learning
echo   prod         Production mode - real telescope data processing
echo   build        Build Docker image
echo   test         Run test suite
echo   help         Show this help
echo.
echo Development Mode Examples:
echo   correlator dev                              Interactive dev CLI
echo   correlator dev run --n-ants 8               Run simulation
echo   correlator dev test                         Run tests
echo.
echo Production Mode Examples:
echo   correlator prod                             Interactive prod CLI
echo   correlator prod stream --source tcp://host:port   Live streaming
echo   correlator prod process --input-dir data/   Process files
echo.
echo For detailed help on each mode:
echo   correlator dev --help
echo   correlator prod --help
echo.
exit /b 0

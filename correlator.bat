@echo off
REM Telescope Correlator - Simple CLI Runner
REM Usage: correlator [command] [options]

SET IMAGE_NAME=telescope-correlator

REM Check if Docker is available
docker --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Docker is not installed or not in PATH
    echo Please install Docker Desktop: https://www.docker.com/products/docker-desktop
    exit /b 1
)

REM Get the command (default to interactive)
SET CMD=%1
IF "%CMD%"=="" SET CMD=interactive

REM Shift to get remaining arguments
SHIFT

REM Handle different commands
IF "%CMD%"=="build" (
    echo Cleaning up old Docker images...
    docker image rm %IMAGE_NAME% >nul 2>&1
    docker image prune -f >nul 2>&1
    echo.
    echo Building Telescope Correlator...
    docker build -f app/Dockerfile -t %IMAGE_NAME% .
    IF %ERRORLEVEL% EQU 0 (
        echo.
        echo ✓ Build successful!
        echo Run 'correlator' to start the CLI
    )
    exit /b %ERRORLEVEL%
)

IF "%CMD%"=="interactive" (
    REM Check if image exists, build if not
    docker image inspect %IMAGE_NAME% >nul 2>&1
    IF %ERRORLEVEL% NEQ 0 (
        echo Image not found. Building...
        docker build -f app/Dockerfile -t %IMAGE_NAME% . -q
    )
    
    echo Starting Interactive CLI...
    echo.
    docker run -it --rm -v "%CD%\dev_workspace\outputs:/app/outputs" %IMAGE_NAME% python -m correlator --interactive
    exit /b %ERRORLEVEL%
)

IF "%CMD%"=="run" (
    REM Check if image exists, build if not
    docker image inspect %IMAGE_NAME% >nul 2>&1
    IF %ERRORLEVEL% NEQ 0 (
        echo Image not found. Building...
        docker build -f app/Dockerfile -t %IMAGE_NAME% . -q
    )
    
    REM Shift removes first argument ('run'), %* now contains only the actual parameters
    echo Running correlator...
    docker run --rm -v "%CD%\dev_workspace\outputs:/app/outputs" %IMAGE_NAME% correlator %1 %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)

IF "%CMD%"=="test" (
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

IF "%CMD%"=="help" (
    goto :help
)

IF "%CMD%"=="-h" (
    goto :help
)

IF "%CMD%"=="--help" (
    goto :help
)

REM Unknown command
echo Unknown command: %CMD%
echo.
goto :help

:help
echo Telescope Correlator CLI
echo.
echo Usage: correlator [COMMAND] [OPTIONS]
echo.
echo Commands:
echo   correlator                    Start interactive CLI (default)
echo   correlator build              Build the Docker image
echo   correlator run [OPTIONS]      Run correlator with parameters
echo   correlator test               Run test suite
echo   correlator help               Show this help
echo.
echo Examples:
echo   correlator                                             Start interactive CLI
echo   correlator build                                       Build Docker image
echo   correlator run --n-ants 4 --n-channels 64              Run with parameters
echo   correlator run --sim-duration 2.0 --output-dir outputs Custom run
echo   correlator test                                        Run all tests
echo.
echo For more options in run mode, use: correlator run --help
exit /b 0

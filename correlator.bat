@echo off
REM Telescope Correlator -- usage: correlator.bat [build|test|validate|help]

SET IMAGE=telescope-correlator
SET VIMAGE=telescope-correlator-validation

IF "%1"=="build" GOTO build
IF "%1"=="test"  GOTO test
IF "%1"=="validate" GOTO validate
IF "%1"=="help"  GOTO help
IF "%1"=="-h"    GOTO help
IF "%1"=="--help" GOTO help
IF "%1"==""      GOTO start

echo Unknown command: %1
GOTO help

:build
echo Building Docker image...
docker build -f app/Dockerfile -t %IMAGE% .
exit /b %ERRORLEVEL%

:test
docker image inspect %IMAGE% >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Image not found. Run 'correlator.bat build' first.
    exit /b 1
)
docker run --rm -v "%CD%:/workspace" -e PYTHONPATH=/workspace/app/src:/usr/local/lib/python3.11/site-packages -w /workspace %IMAGE% pytest tests_harness/ -v
exit /b %ERRORLEVEL%

:validate
REM Separate image carrying the pyuvsim reference stack; see validation/.
docker build -f validation/Dockerfile -t %VIMAGE% .
IF %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%
IF NOT EXIST "validation\reports" mkdir "validation\reports"
docker run --rm -v "%CD%\validation\reports:/app/reports" %VIMAGE% python -m pytest ../tests_harness -q -p no:cacheprovider
IF %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%
docker run --rm -v "%CD%\validation\reports:/app/reports" %VIMAGE% python run_validation.py --with-pyuvsim --json ../reports/validation.json
exit /b %ERRORLEVEL%

:help
echo Usage: correlator.bat [build^|test^|validate^|help]
echo   build      Build the Docker image
echo   test       Run the test suite
echo   validate   Validate against analytic theory and pyuvsim
echo   help       Show this message
echo   (none)     Start the interactive CLI
exit /b 0

:start
docker image inspect %IMAGE% >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Image not found. Run 'correlator.bat build' first.
    exit /b 1
)
docker run -it --rm -v "%CD%\workspace:/workspace" %IMAGE% python -m correlator
exit /b %ERRORLEVEL%

@echo off
setlocal

echo Building the app image (first run only -- takes a few minutes)...
docker build -t revenue-scenario-planner .
if errorlevel 1 (
    echo.
    echo Docker build failed. Make sure Docker Desktop is installed and running,
    echo then try again.
    pause
    exit /b 1
)

echo Starting the app...
docker run --rm -d -p 8501:8501 --name revenue-scenario-planner-app revenue-scenario-planner >nul

echo Waiting for the app to be ready...
:waitloop
curl -s -o nul http://localhost:8501
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto waitloop
)

start "" http://localhost:8501
echo.
echo The app is running at http://localhost:8501
echo To stop it later, run: docker stop revenue-scenario-planner-app
pause

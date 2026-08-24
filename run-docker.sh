#!/usr/bin/env bash
set -e

echo "Building the app image (first run only -- takes a few minutes)..."
docker build -t revenue-scenario-planner .

echo "Starting the app..."
docker run --rm -d -p 8501:8501 --name revenue-scenario-planner-app revenue-scenario-planner >/dev/null

echo "Waiting for the app to be ready..."
for i in $(seq 1 60); do
    if curl -s -o /dev/null http://localhost:8501; then
        break
    fi
    sleep 1
done

if command -v open >/dev/null 2>&1; then
    open http://localhost:8501
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open http://localhost:8501
fi

echo ""
echo "The app is running at http://localhost:8501"
echo "To stop it later, run: docker stop revenue-scenario-planner-app"

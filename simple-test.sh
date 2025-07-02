#\!/bin/bash
echo "Starting Twitch Miner Docker Test"
echo "=================================="
docker-compose down 2>/dev/null || true
echo "Building and starting container..."
docker-compose up --build

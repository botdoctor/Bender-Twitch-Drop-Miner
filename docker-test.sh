#!/bin/bash

echo "🐳 Starting Twitch Miner Docker Test"
echo "======================================="

# Clean up any existing containers
echo "🧹 Cleaning up existing containers..."
docker-compose down -v 2>/dev/null || true
docker rm -f twitch-miner 2>/dev/null || true

# Create directories for persistence
echo "📁 Creating directories..."
mkdir -p logs cookies

# Set environment variables for test
export TWITCH_USERNAME=treaclefamousn6g
export STREAMER_FILE=ruststreamers.txt
export DISCORD_WEBHOOK=""

echo "🔧 Configuration:"
echo "  Username: $TWITCH_USERNAME"
echo "  Streamer file: $STREAMER_FILE"
echo "  Log directory: ./logs"
echo "  Cookie directory: ./cookies"

echo ""
echo "🚀 Starting Docker build and run..."
echo "   This will take a few minutes for the first build (Chrome installation)"
echo "   Watch for automated login messages!"
echo ""

# Build and run with logs
docker-compose up --build 2>&1 | tee logs/docker-test-$(date +%Y%m%d-%H%M%S).log

echo ""
echo "🏁 Test completed. Check the logs above for:"
echo "  ✓ Activation code generation (XXXXXXXX format)"
echo "  ✓ 'Created activation_code.txt for automated login'"
echo "  ✓ 'Starting automated login process...'"
echo "  ✓ Selenium browser automation logs"
echo "  ✓ 'Login successful' or error messages"
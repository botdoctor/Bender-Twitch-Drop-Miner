#!/bin/bash

echo "⚡ Quick Twitch Miner Authentication Test"
echo "========================================"

# Build the image in background if it doesn't exist
if ! docker images | grep -q "twitch-miner"; then
    echo "🔨 Building Docker image (this will take a few minutes)..."
    docker-compose build > build.log 2>&1 &
    BUILD_PID=$!
    
    # Show progress
    while kill -0 $BUILD_PID 2>/dev/null; do
        echo -n "."
        sleep 5
    done
    echo " Build complete!"
fi

echo ""
echo "🚀 Starting test run..."
echo "   - Will generate TV activation code"
echo "   - Will attempt automated login"
echo "   - Press Ctrl+C to stop"
echo ""

# Run with timeout and capture logs
timeout 300 docker-compose up 2>&1 | tee /tmp/twitch-test.log | while read line; do
    echo "$line"
    
    # Highlight important events
    if echo "$line" | grep -q "enter this code"; then
        echo "🎯 ACTIVATION CODE GENERATED!"
    elif echo "$line" | grep -q "Created activation_code.txt"; then
        echo "✅ AUTOMATION TRIGGERED!"
    elif echo "$line" | grep -q "Starting automated login"; then
        echo "🤖 SELENIUM STARTED!"
    elif echo "$line" | grep -q -i "login.*success\|authentication.*success"; then
        echo "🎉 LOGIN SUCCESS!"
    elif echo "$line" | grep -q -i "error\|failed"; then
        echo "⚠️  ERROR DETECTED"
    fi
done

echo ""
echo "📊 Test Summary:"
echo "==============="

# Check what happened
if grep -q "enter this code" /tmp/twitch-test.log; then
    CODE=$(grep "enter this code" /tmp/twitch-test.log | sed 's/.*code: //' | tail -1)
    echo "✅ Activation code generated: $CODE"
else
    echo "❌ No activation code generated"
fi

if grep -q "Created activation_code.txt" /tmp/twitch-test.log; then
    echo "✅ Automation was triggered"
else
    echo "❌ Automation was not triggered"
fi

if grep -q "Starting automated login" /tmp/twitch-test.log; then
    echo "✅ Selenium process started"
else
    echo "❌ Selenium process did not start"
fi

if grep -q -i "login.*success\|authentication.*success" /tmp/twitch-test.log; then
    echo "✅ Login appeared successful"
else
    echo "⏳ Login still in progress or failed"
fi

echo ""
echo "💾 Full logs saved to: /tmp/twitch-test.log"
echo "🔍 To check live logs: ./docker-logs.sh live"
echo "🛑 To stop: docker-compose down"
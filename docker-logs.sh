#!/bin/bash

echo "📊 Twitch Miner Docker Logs Monitor"
echo "===================================="

# Function to show recent logs
show_logs() {
    echo "🔍 Recent logs from Docker container:"
    echo "-------------------------------------"
    docker-compose logs --tail=50 twitch-miner
}

# Function to monitor live logs
monitor_logs() {
    echo "📡 Monitoring live logs (Ctrl+C to stop):"
    echo "----------------------------------------"
    docker-compose logs -f twitch-miner
}

# Function to check container status
check_status() {
    echo "🏥 Container status:"
    echo "-------------------"
    docker-compose ps
    echo ""
    
    if docker-compose ps | grep -q "Up"; then
        echo "✅ Container is running"
    else
        echo "❌ Container is not running"
    fi
}

# Function to search for authentication events
check_auth() {
    echo "🔐 Authentication events:"
    echo "------------------------"
    
    # Check for activation codes
    echo "Activation codes generated:"
    docker-compose logs twitch-miner 2>/dev/null | grep -i "enter this code" || echo "  No codes found yet"
    
    echo ""
    echo "Automation triggers:"
    docker-compose logs twitch-miner 2>/dev/null | grep -i "automated login" || echo "  No automation events found"
    
    echo ""
    echo "Login results:"
    docker-compose logs twitch-miner 2>/dev/null | grep -i "login.*success\|authentication.*success\|logged in" || echo "  No successful logins found"
    
    echo ""
    echo "Error events:"
    docker-compose logs twitch-miner 2>/dev/null | grep -i "error\|failed\|exception" | tail -5 || echo "  No recent errors"
}

# Main menu
case "$1" in
    "live")
        monitor_logs
        ;;
    "auth")
        check_auth
        ;;
    "status")
        check_status
        ;;
    "recent")
        show_logs
        ;;
    *)
        echo "Usage: $0 [live|auth|status|recent]"
        echo ""
        echo "Commands:"
        echo "  live    - Monitor live logs"
        echo "  auth    - Check authentication events"
        echo "  status  - Check container status"
        echo "  recent  - Show recent logs"
        echo ""
        echo "Quick status:"
        check_status
        ;;
esac
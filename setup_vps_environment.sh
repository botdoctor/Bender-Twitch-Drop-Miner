#!/bin/bash

# VPS Environment Setup Script
# This script sets up the environment similar to an Ubuntu VPS

set -e

echo "🚀 Setting up VPS-like environment for Twitch Mining"
echo "=================================================="

# Update system packages
echo "📦 Updating system packages..."
if command -v apt-get &> /dev/null; then
    sudo apt-get update -y
    sudo apt-get upgrade -y
elif command -v yum &> /dev/null; then
    sudo yum update -y
elif command -v pacman &> /dev/null; then
    sudo pacman -Syu --noconfirm
fi

# Install Python and pip if not already installed
echo "🐍 Installing Python dependencies..."
if command -v apt-get &> /dev/null; then
    sudo apt-get install -y python3 python3-pip python3-venv
elif command -v yum &> /dev/null; then
    sudo yum install -y python3 python3-pip
elif command -v pacman &> /dev/null; then
    sudo pacman -S --noconfirm python python-pip
fi

# Install Chrome for headless operation
echo "🌐 Installing Google Chrome..."
if command -v apt-get &> /dev/null; then
    # Ubuntu/Debian
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
    sudo apt-get update -y
    sudo apt-get install -y google-chrome-stable
elif command -v yum &> /dev/null; then
    # CentOS/RHEL
    sudo yum install -y wget
    wget https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm
    sudo yum localinstall -y google-chrome-stable_current_x86_64.rpm
    rm google-chrome-stable_current_x86_64.rpm
fi

# Install ChromeDriver
echo "🔧 Installing ChromeDriver..."
CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d'.' -f1)
echo "Detected Chrome version: $CHROME_VERSION"

# Get latest ChromeDriver version for this Chrome version
CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}")
echo "Installing ChromeDriver version: $CHROMEDRIVER_VERSION"

wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip"
sudo unzip /tmp/chromedriver.zip -d /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver
rm /tmp/chromedriver.zip

# Verify ChromeDriver installation
echo "✅ ChromeDriver installed: $(chromedriver --version)"

# Install additional system dependencies
echo "📋 Installing additional dependencies..."
if command -v apt-get &> /dev/null; then
    sudo apt-get install -y \
        xvfb \
        unzip \
        curl \
        wget \
        gnupg \
        software-properties-common \
        build-essential \
        libgconf-2-4 \
        libxss1 \
        libappindicator1 \
        fonts-liberation \
        libasound2 \
        libatk-bridge2.0-0 \
        libdrm2 \
        libxcomposite1 \
        libxdamage1 \
        libxrandr2 \
        libgbm1 \
        libxkbcommon0 \
        libgtk-3-0
fi

# Create virtual environment
echo "🔧 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python requirements
echo "📦 Installing Python packages..."
pip install --upgrade pip

# Install required packages for the mining system
pip install \
    selenium \
    requests \
    colorama \
    beautifulsoup4 \
    lxml \
    websockets \
    aiohttp \
    python-dateutil \
    pytz

# Create systemd service file for automatic startup (optional)
echo "⚙️ Creating systemd service file..."
cat > twitch_miner.service << EOF
[Unit]
Description=Multi-Account Twitch Channel Points Miner
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python multi_account_manager.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "📁 Creating directory structure..."
mkdir -p accounts
mkdir -p logs
mkdir -p backup

# Set up log rotation
echo "📋 Setting up log rotation..."
cat > logrotate.conf << EOF
$(pwd)/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    notifempty
    create 644 $USER $USER
}

$(pwd)/accounts/*/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    notifempty
    create 644 $USER $USER
}
EOF

# Create firewall rules for analytics ports (if UFW is available)
if command -v ufw &> /dev/null; then
    echo "🔥 Setting up firewall rules for analytics ports..."
    for port in {5000..5010}; do
        sudo ufw allow $port/tcp comment "Twitch Analytics Port $port"
    done
fi

# Test Chrome in headless mode
echo "🧪 Testing headless Chrome..."
cat > test_chrome.py << EOF
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')

try:
    driver = webdriver.Chrome(options=options)
    driver.get('https://www.google.com')
    print(f"✅ Chrome test successful - Title: {driver.title}")
    driver.quit()
except Exception as e:
    print(f"❌ Chrome test failed: {e}")
EOF

python test_chrome.py
rm test_chrome.py

echo ""
echo "🎉 VPS Environment Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Update pass.txt with your account credentials"
echo "3. Test the system: python test_multi_account.py"
echo "4. Run the mining system: python multi_account_manager.py"
echo ""
echo "System service commands:"
echo "- Install service: sudo cp twitch_miner.service /etc/systemd/system/"
echo "- Enable service: sudo systemctl enable twitch_miner"
echo "- Start service: sudo systemctl start twitch_miner"
echo "- Check status: sudo systemctl status twitch_miner"
echo ""
echo "Analytics will be available at:"
echo "- Account 1: http://YOUR_VPS_IP:5000"
echo "- Account 2: http://YOUR_VPS_IP:5001"
echo "- Account 3: http://YOUR_VPS_IP:5002"
echo "- etc..."
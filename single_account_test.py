#!/usr/bin/env python3
"""
Simple Single Account Test Script
Usage: python3 single_account_test.py
"""

import os
import logging
from pathlib import Path
from TwitchChannelPointsMiner import TwitchChannelPointsMiner
from TwitchChannelPointsMiner.logger import LoggerSettings, ColorPalette
from TwitchChannelPointsMiner.classes.Chat import ChatPresence
from TwitchChannelPointsMiner.classes.Settings import Priority, FollowersOrder
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer, StreamerSettings

def single_account_test():
    """Test with a single account using minimal configuration"""
    
    # Simple configuration - you can modify these values
    username = input("Enter your Twitch username: ")
    password = input("Enter your Twitch password (or press Enter to use environment variable): ") or os.getenv('TWITCH_PASSWORD', 'your-password-here')
    
    # Create a simple streamers list for testing
    test_streamers = [
        "shroud",
        "summit1g", 
        "xqcow"
    ]
    
    print(f"\n🎮 Starting Twitch Channel Points Miner for: {username}")
    print(f"📺 Watching streamers: {', '.join(test_streamers)}")
    print("🔧 Using minimal test configuration")
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    # Initialize TwitchChannelPointsMiner with minimal settings for testing
    twitch_miner = TwitchChannelPointsMiner(
        username=username,
        password=password,
        claim_drops_startup=True,
        priority=[Priority.ORDER],
        enable_analytics=True,
        disable_ssl_cert_verification=False,
        logger_settings=LoggerSettings(
            save=True,
            console_level=logging.INFO,
            console_username=True,
            auto_clear=True,
            file_level=logging.DEBUG,
            emoji=True,
            less=False,
            colored=True,
            color_palette=ColorPalette(
                STREAMER_online="GREEN",
                streamer_offline="red"
            )
        ),
        streamer_settings=StreamerSettings(
            make_predictions=False,        # Disable betting for safety during testing
            follow_raid=True,
            claim_drops=True,
            claim_moments=False,
            watch_streak=True,
            community_goals=False,
            chat=ChatPresence.ONLINE
        )
    )
    
    # Start analytics server on port 5000
    try:
        twitch_miner.analytics(host="127.0.0.1", port=5000, refresh=5, days_ago=7)
        print("📊 Analytics server started on http://127.0.0.1:5000")
    except Exception as e:
        print(f"⚠️  Analytics server failed to start: {e}")
        print("Continuing without analytics...")
    
    # Convert streamers to Streamer objects for better control
    streamers = [Streamer(username) for username in test_streamers]
    
    print("\n🚀 Starting the miner...")
    print("Press Ctrl+C to stop")
    
    # Start mining
    try:
        twitch_miner.mine(
            streamers,
            followers=False,
            followers_order=FollowersOrder.ASC
        )
    except KeyboardInterrupt:
        print("\n⏹️  Stopping miner...")
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        print("Check the logs for more details")

if __name__ == "__main__":
    print("🧪 Single Account Twitch Miner Test")
    print("=" * 40)
    print("This script will test the miner with a single account")
    print("It uses minimal configuration for safe testing")
    print("=" * 40)
    
    single_account_test()
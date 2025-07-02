# -*- coding: utf-8 -*-

import logging
import os
import sys
import argparse
from pathlib import Path
from colorama import Fore
from TwitchChannelPointsMiner import TwitchChannelPointsMiner
from TwitchChannelPointsMiner.logger import LoggerSettings, ColorPalette
from TwitchChannelPointsMiner.classes.Chat import ChatPresence
from TwitchChannelPointsMiner.classes.Discord import Discord
from TwitchChannelPointsMiner.classes.Webhook import Webhook
from TwitchChannelPointsMiner.classes.Telegram import Telegram
from TwitchChannelPointsMiner.classes.Matrix import Matrix
from TwitchChannelPointsMiner.classes.Pushover import Pushover
from TwitchChannelPointsMiner.classes.Gotify import Gotify
from TwitchChannelPointsMiner.classes.Settings import Priority, Events, FollowersOrder
from TwitchChannelPointsMiner.classes.entities.Bet import Strategy, BetSettings, Condition, OutcomeKeys, FilterCondition, DelayMode
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer, StreamerSettings

def get_account_config():
    """Get account configuration from command line arguments or environment variables"""
    parser = argparse.ArgumentParser(description="Twitch Channel Points Miner")
    parser.add_argument("--username", help="Twitch username")
    parser.add_argument("--streamers-file", help="File containing streamer usernames")
    parser.add_argument("--analytics-port", type=int, default=5000, help="Analytics server port")
    parser.add_argument("--workspace", help="Account workspace directory")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode (prompt for inputs)")
    
    args = parser.parse_args()
    
    # Get configuration from arguments, environment variables, or interactive input
    if args.interactive or (not args.username and not os.getenv('ACCOUNT_USERNAME')):
        usernamedata = input("What is the username?: ")
        filename = input("Where would you like to pull the streamers from?: ")
        analytics_port = 5000
        workspace_dir = None
    else:
        usernamedata = args.username or os.getenv('ACCOUNT_USERNAME')
        filename = args.streamers_file or os.getenv('STREAMERS_FILE', 'ruststreamers.txt')
        analytics_port = args.analytics_port or int(os.getenv('ANALYTICS_PORT', '5000'))
        workspace_dir = args.workspace or os.getenv('WORKSPACE_DIR')
        
    return usernamedata, filename, analytics_port, workspace_dir

def setup_account_workspace(username, workspace_dir):
    """Setup account-specific workspace and return paths"""
    if workspace_dir:
        # Create workspace directory if it doesn't exist
        Path(workspace_dir).mkdir(parents=True, exist_ok=True)
        
        # Account-specific file paths
        cookies_file = os.path.join(workspace_dir, "cookies.pkl")
        logs_dir = os.path.join(workspace_dir, "logs")
        Path(logs_dir).mkdir(exist_ok=True)
        
        return cookies_file, logs_dir
    else:
        # Use default locations
        return f"cookies_{username}.pkl", "logs"

# Get account configuration
usernamedata, filename, analytics_port, workspace_dir = get_account_config()
cookies_file, logs_dir = setup_account_workspace(usernamedata, workspace_dir)
twitch_miner = TwitchChannelPointsMiner(
    username=usernamedata,
    password=os.getenv('ACCOUNT_PASSWORD', "write-your-secure-psw"),  # Password from environment or interactive
    claim_drops_startup=True,                  # If you want to auto claim all drops from Twitch inventory on the startup
    priority=[                                  # Custom priority in this case for example
        Priority.DROPS,                         # - When we don't have anymore watch streak to catch, wait until all drops are collected over the streamers
        Priority.ORDER                          # - When we have all of the drops claimed and no watch-streak available, use the order priority (POINTS_ASCENDING, POINTS_DESCENDING)
    ],
    enable_analytics=True,                     # Disables Analytics if False. Disabling it significantly reduces memory consumption
    disable_ssl_cert_verification=False,        # Set to True at your own risk and only to fix SSL: CERTIFICATE_VERIFY_FAILED error
    disable_at_in_nickname=False,               # Set to True if you want to check for your nickname mentions in the chat even without @ sign
    logger_settings=LoggerSettings(
        save=True,                              # If you want to save logs in a file (suggested)
        console_level=logging.INFO,             # Level of logs - use logging.DEBUG for more info
        console_username=True,                 # Adds a username to every console log line if True. Also adds it to Telegram, Discord, etc. Useful when you have several accounts
        auto_clear=True,                        # Create a file rotation handler with interval = 1D and backupCount = 7 if True (default)
        time_zone="",                           # Set a specific time zone for console and file loggers. Use tz database names. Example: "America/Denver"
        file_level=logging.DEBUG,               # Level of logs - If you think the log file it's too big, use logging.INFO
        emoji=True,                             # On Windows, we have a problem printing emoji. Set to false if you have a problem
        less=False,                             # If you think that the logs are too verbose, set this to True
        colored=True,                           # If you want to print colored text
        # logs_file parameter doesn't exist in LoggerSettings
        color_palette=ColorPalette(             # You can also create a custom palette color (for the common message).
            STREAMER_online="GREEN",            # Don't worry about lower/upper case. The script will parse all the values.
            streamer_offline="red",             # Read more in README.md
            BET_wiN=Fore.MAGENTA                # Color allowed are: [BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET].
        ),
        telegram=None,  # Disabled for multi-account to avoid spam
        discord=None,   # Disabled for multi-account to avoid spam
        webhook=None,   # Disabled for multi-account to avoid spam
        matrix=None,    # Disabled for multi-account to avoid spam
        pushover=None,  # Disabled for multi-account to avoid spam
        gotify=None     # Disabled for multi-account to avoid spam
    ),
    streamer_settings=StreamerSettings(
        make_predictions=False,                  # If you want to Bet / Make prediction
        follow_raid=True,                       # Follow raid to obtain more points
        claim_drops=True,                       # We can't filter rewards base on stream. Set to False for skip viewing counter increase and you will never obtain a drop reward from this script. Issue #21
        claim_moments=False,                     # If set to True, https://help.twitch.tv/s/article/moments will be claimed when available
        watch_streak=False,                      # If a streamer go online change the priority of streamers array and catch the watch screak. Issue #11
        community_goals=False,                  # If True, contributes the max channel points per stream to the streamers' community challenge goals
        chat=ChatPresence.ONLINE,               # Join irc chat to increase watch-time [ALWAYS, NEVER, ONLINE, OFFLINE]
        bet=BetSettings(
            strategy=Strategy.SMART,            # Choose you strategy!
            percentage=5,                       # Place the x% of your channel points
            percentage_gap=20,                  # Gap difference between outcomesA and outcomesB (for SMART strategy)
            max_points=50000,                   # If the x percentage of your channel points is gt bet_max_points set this value
            stealth_mode=True,                  # If the calculated amount of channel points is GT the highest bet, place the highest value minus 1-2 points Issue #33
            delay_mode=DelayMode.FROM_END,      # When placing a bet, we will wait until `delay` seconds before the end of the timer
            delay=6,
            minimum_points=20000,               # Place the bet only if we have at least 20k points. Issue #113
            filter_condition=FilterCondition(
                by=OutcomeKeys.TOTAL_USERS,     # Where apply the filter. Allowed [PERCENTAGE_USERS, ODDS_PERCENTAGE, ODDS, TOP_POINTS, TOTAL_USERS, TOTAL_POINTS]
                where=Condition.LTE,            # 'by' must be [GT, LT, GTE, LTE] than value
                value=800
            )
        )
    )
)

# You can customize the settings for each streamer. If not settings were provided, the script would use the streamer_settings from TwitchChannelPointsMiner.
# If no streamer_settings are provided in TwitchChannelPointsMiner the script will use default settings.
# The streamers array can be a String -> username or Streamer instance.

# The settings priority are: settings in mine function, settings in TwitchChannelPointsMiner instance, default settings.
# For example, if in the mine function you don't provide any value for 'make_prediction' but you have set it on TwitchChannelPointsMiner instance, the script will take the value from here.
# If you haven't set any value even in the instance the default one will be used

# Enable analytics with account-specific port
if analytics_port > 0:
    try:
        twitch_miner.analytics(host="127.0.0.1", port=analytics_port, refresh=5, days_ago=7)
        print(f"Analytics server started on port {analytics_port} for account {usernamedata}")
    except Exception as e:
        print(f"Failed to start analytics server on port {analytics_port}: {e}")
        print("Continuing without analytics server...")



try:
	with open(filename, "r") as file:
		streamer_usernames = [line.strip() for line in file]
except FileNotFoundError:
	print(f"Error: The file '{filename}' was not found.")
	exit(1) # Exit if file does not exist


streamers = [Streamer(username) if i < 5 else username for i, username in enumerate(streamer_usernames)]


twitch_miner.mine(
    streamers,                          # Use the list of streamers from a file
    followers=False,                    # Automatic download the list of your followers
    followers_order=FollowersOrder.ASC  # Sort the followers list by follow date. ASC or DESC
)

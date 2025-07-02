# -*- coding: utf-8 -*-

import logging
import re
import configparser
import os
import platform
import json
import time
if platform.system() == "Windows":
    import msvcrt
else:
    import fcntl
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

# Custom logger to capture activation code
class ActivationCodeLogger(logging.Logger):
    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)
        self.activation_code = None
        self.username = None  # Store the username for verification

    def set_username(self, username):
        self.username = username

    def info(self, msg, *args, **kwargs):
        super().info(msg, *args, **kwargs)
        # Look for activation code in the message
        match = re.search(r"enter this code: (\w+)", str(msg))
        if match and self.username:
            self.activation_code = match.group(1)
            # Save code and username to a file for login.py with file locking
            code_data = {"username": self.username, "code": self.activation_code}
            with open("activation_code.txt", "w") as f:
                if platform.system() == "Windows":
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1024)
                else:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                json.dump(code_data, f)
                f.flush()  # Ensure the file is written
                if platform.system() == "Windows":
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1024)
                else:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            logger.info(f"Captured activation code for {self.username}: {self.activation_code}")
            # Call login.py to process the code - use the right Python command for your system
            try:
                if platform.system() == "Windows":
                    python_cmd = "python"  # Windows typically uses "python" not "python3"
                else:
                    python_cmd = "python3"
                    
                result = os.system(f"{python_cmd} login.py")
                if result == 0:
                    logger.info("Successfully executed login.py to process the activation code")
                else:
                    logger.warning(f"login.py exited with code {result}")
            except Exception as e:
                logger.error(f"Failed to execute login.py: {e}")

# Set custom logger
logging.setLoggerClass(ActivationCodeLogger)
logger = logging.getLogger(__name__)

# Read username and password from pass.txt
try:
    with open("pass.txt", "r") as f:
        if platform.system() == "Windows":
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1024)
        else:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        line = f.readline().strip()
        if platform.system() == "Windows":
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1024)
        else:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        if ":" not in line:
            print("Error: pass.txt must contain username:password")
            exit(1)
        usernamedata, password = line.split(":", 1)
    logger.info(f"twitch_miner.py will use account: {usernamedata}")
except FileNotFoundError:
    print("Error: pass.txt not found")
    exit(1)

# Read streamer file from config.txt
try:
    config = configparser.ConfigParser()
    config.read("config.txt")
    filename = config.get("DEFAULT", "streamer_file", fallback=None)
    if not filename:
        print("Error: streamer_file not specified in config.txt")
        exit(1)
except FileNotFoundError:
    print("Error: config.txt not found")
    exit(1)
except configparser.MissingSectionHeaderError:
    print("Error: config.txt is missing section headers. It should contain [DEFAULT] followed by key-value pairs.")
    exit(1)

twitch_miner = TwitchChannelPointsMiner(
    username=usernamedata,
    password=password,
    claim_drops_startup=True,
    priority=[
        Priority.DROPS,
        Priority.ORDER
    ],
    enable_analytics=True,
    disable_ssl_cert_verification=False,
    disable_at_in_nickname=False,
    logger_settings=LoggerSettings(
        save=True,
        console_level=logging.INFO,
        console_username=True,
        auto_clear=True,
        time_zone="",
        file_level=logging.DEBUG,
        emoji=True,
        less=False,
        colored=True,
        color_palette=ColorPalette(
            STREAMER_online="GREEN",
            streamer_offline="red",
            BET_wiN=Fore.MAGENTA
        ),
        telegram=Telegram(
            chat_id=123456789,
            token="123456789:shfuihreuifheuifhiu34578347",
            events=[Events.STREAMER_ONLINE, Events.STREAMER_OFFLINE,
                    Events.BET_LOSE, Events.CHAT_MENTION],
            disable_notification=True,
        ),
        discord=Discord(
            webhook_api="https://discord.com/api/webhooks/1305673224100642877/zLiaMVlkRGxoG5EjKcMw0Ktnx3gjhxTgSomrvQnP8uYVyJtGTRGEToDufvPK_AHtXVad",
            events=[Events.STREAMER_ONLINE, Events.STREAMER_OFFLINE,
                    Events.BET_LOSE, Events.CHAT_MENTION, Events.DROP_CLAIM],
        ),
        webhook=Webhook(
            endpoint="https://example.com/webhook",
            method="GET",
            events=[Events.STREAMER_ONLINE, Events.STREAMER_OFFLINE,
                    Events.BET_LOSE, Events.CHAT_MENTION],
        ),
        matrix=Matrix(
            username="twitch_miner",
            password="...",
            homeserver="matrix.org",
            room_id="...",
            events=[Events.STREAMER_ONLINE, Events.STREAMER_OFFLINE, Events.BET_LOSE],
        ),
        pushover=Pushover(
            userkey="YOUR-ACCOUNT-TOKEN",
            token="YOUR-APPLICATION-TOKEN",
            priority=0,
            sound="pushover",
            events=[Events.CHAT_MENTION, Events.DROP_CLAIM],
        ),
        gotify=Gotify(
            endpoint="https://example.com/message?token=TOKEN",
            priority=8,
            events=[Events.STREAMER_ONLINE, Events.STREAMER_OFFLINE,
                    Events.BET_LOSE, Events.CHAT_MENTION],
        )
    ),
    streamer_settings=StreamerSettings(
        make_predictions=False,
        follow_raid=True,
        claim_drops=True,
        claim_moments=False,
        watch_streak=False,
        community_goals=False,
        chat=ChatPresence.ONLINE,
        bet=BetSettings(
            strategy=Strategy.SMART,
            percentage=5,
            percentage_gap=20,
            max_points=50000,
            stealth_mode=True,
            delay_mode=DelayMode.FROM_END,
            delay=6,
            minimum_points=20000,
            filter_condition=FilterCondition(
                by=OutcomeKeys.TOTAL_USERS,
                where=Condition.LTE,
                value=800
            )
        )
    )
)

# Set the username in the logger
logger_instance = logging.getLogger(__name__)
logger_instance.set_username(usernamedata)

# Read streamers from file
try:
    with open(filename, "r") as file:
        streamer_usernames = [line.strip() for line in file if line.strip()]
except FileNotFoundError:
    print(f"Error: The file '{filename}' was not found.")
    exit(1)

streamers = [Streamer(username) if i < 5 else username for i, username in enumerate(streamer_usernames)]

twitch_miner.mine(
    streamers,
    followers=False,
    followers_order=FollowersOrder.ASC
)
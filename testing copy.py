
# -*- coding: utf-8 -*-
import logging
import multiprocessing
import os
import time
import sys
from colorama import Fore
from TwitchChannelPointsMiner import TwitchChannelPointsMiner
from TwitchChannelPointsMiner.logger import LoggerSettings, ColorPalette
from TwitchChannelPointsMiner.classes.Chat import ChatPresence
from TwitchChannelPointsMiner.classes.Discord import Discord
from TwitchChannelPointsMiner.classes.Settings import Priority, Events, FollowersOrder
from TwitchChannelPointsMiner.classes.entities.Bet import Strategy, BetSettings, Condition, OutcomeKeys, FilterCondition, DelayMode
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer, StreamerSettings

def read_config():
    """Read config.txt for streamer file."""
    config_file = "config.txt"
    if not os.path.exists(config_file):
        print(f"Error: {config_file} not found. Creating a default config.")
        with open(config_file, "w") as f:
            f.write("streamer_file=rust39.txt\n")
        return "rust39.txt"
    try:
        with open(config_file, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("streamer_file="):
                    streamer_file = line.split("=", 1)[1]
                    if streamer_file:
                        return streamer_file
        print(f"Error: 'streamer_file' not found in {config_file}. Using default 'rust39.txt'.")
        with open(config_file, "a") as f:
            f.write("streamer_file=rust39.txt\n")
        return "rust39.txt"
    except Exception as e:
        print(f"Error reading {config_file}: {e}")
        sys.exit(1)

def read_accounts():
    """Read accounts from results.txt."""
    accounts = []
    try:
        with open("results.txt", "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    username, password = line.split(":")
                    accounts.append({"username": username, "password": password})
        return accounts
    except FileNotFoundError:
        print("Error: results.txt not found.")
        sys.exit(1)
    except ValueError:
        print("Error: Invalid format in results.txt. Use username:password.")
        sys.exit(1)

def read_streamers(filename):
    """Read streamers from the specified file."""
    try:
        with open(filename, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: Streamer file '{filename}' not found.")
        sys.exit(1)

def authenticate_account(account):
    """Authenticate a single account, handling 2FA code."""
    username = account["username"]
    password = account["password"]
    print(f"[{time.ctime()}] Authenticating {username}...")
    
    # Initialize miner to trigger login
    twitch_miner = TwitchChannelPointsMiner(
        username=username,
        password=password,
        claim_drops_startup=True,
        priority=[Priority.DROPS, Priority.ORDER],
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
            discord=Discord(
                webhook_api="https://discord.com/api/webhooks/1305673224100642877/zLiaMVlkRGxoG5EjKcMw0Ktnx3gjhxTgSomrvQnP8uYVyJtGTRGEToDufvPK_AHtXVad",
                events=[Events.STREAMER_ONLINE, Events.STREAMER_OFFLINE, Events.BET_LOSE, Events.CHAT_MENTION, Events.DROP_CLAIM]
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
    
    # The miner outputs the 2FA code to stdout (e.g., "and enter this code: WKKZCCTH").
    # Prompt user to enter it at twitch.tv/activate.
    print(f"[{time.ctime()}] For {username}, look above for the 2FA code (e.g., WKKZCCTH).")
    print(f"Enter this code at https://www.twitch.tv/activate in a browser.")
    input(f"Press Enter after entering the 2FA code for {username} at https://www.twitch.tv/activate: ")
    
    # Check if cookies were created
    cookie_path = f"cookies/{username}.pkl"
    if os.path.exists(cookie_path):
        print(f"[{time.ctime()}] Authentication successful for {username}. Cookies saved to {cookie_path}.")
        return True
    else:
        print(f"[{time.ctime()}] Authentication failed for {username}. No cookies found.")
        return False

def run_miner(account, streamer_file, start_time, timeout=3600):
    """Run miner for a single account with timeout."""
    username = account["username"]
    password = account["password"]
    print(f"[{time.ctime()}] Starting miner for {username}.")

    twitch_miner = TwitchChannelPointsMiner(
        username=username,
        password=password,
        claim_drops_startup=True,
        priority=[Priority.DROPS, Priority.ORDER],
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
            discord=Discord(
                webhook_api="https://discord.com/api/webhooks/1305673224100642877/zLiaMVlkRGxoG5EjKcMw0Ktnx3gjhxTgSomrvQnP8uYVyJtGTRGEToDufvPK_AHtXVad",
                events=[Events.STREAMER_ONLINE, Events.STREAMER_OFFLINE, Events.BET_LOSE, Events.CHAT_MENTION, Events.DROP_CLAIM]
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

    streamer_usernames = read_streamers(streamer_file)
    streamers = [Streamer(username) if i < 5 else username for i, username in enumerate(streamer_usernames)]
    
    try:
        if time.time() - start_time > timeout:
            print(f"[{time.ctime()}] Timeout reached for {username}. Stopping miner.")
            return
        twitch_miner.mine(
            streamers,
            followers=False,
            followers_order=FollowersOrder.ASC
        )
    except Exception as e:
        print(f"[{time.ctime()}] Error running miner for {username}: {e}")

def main():
    """Main function to authenticate and run miners concurrently."""
    streamer_file = read_config()
    accounts = read_accounts()
    
    # Authenticate each account sequentially
    authenticated_accounts = []
    for account in accounts:
        if authenticate_account(account):
            authenticated_accounts.append(account)
        else:
            print(f"[{time.ctime()}] Skipping {account['username']} due to authentication failure.")
    
    if not authenticated_accounts:
        print(f"[{time.ctime()}] No accounts authenticated. Exiting.")
        sys.exit(1)
    
    # Run miners concurrently for authenticated accounts
    start_time = time.time()
    processes = []
    for account in authenticated_accounts:
        p = multiprocessing.Process(target=run_miner, args=(account, streamer_file, start_time))
        processes.append(p)
        p.start()
    
    # Wait for all processes to complete
    for p in processes:
        p.join()

if __name__ == "__main__":
    # Ensure cookies directory exists
    os.makedirs("cookies", exist_ok=True)
    main()

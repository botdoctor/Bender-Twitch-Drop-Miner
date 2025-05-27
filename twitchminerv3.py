import logging
import os
from colorama import Fore
from TwitchChannelPointsMiner import TwitchChannelPointsMiner
from TwitchChannelPointsMiner.logger import LoggerSettings, ColorPalette
from TwitchChannelPointsMiner.classes.Chat import ChatPresence
from TwitchChannelPointsMiner.classes.Discord import Discord
from TwitchChannelPointsMiner.classes.Telegram import Telegram
from TwitchChannelPointsMiner.classes.Settings import Priority, Events, FollowersOrder
from TwitchChannelPointsMiner.classes.entities.Bet import Strategy, BetSettings, Condition, OutcomeKeys, FilterCondition, DelayMode
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer, StreamerSettings

# Function to load streamers from a file
def load_streamers_from_file(file_path):
    with open(file_path, "r") as file:
        return [line.strip() for line in file.readlines()]

# Function to check if a streamer is playing Rust
def is_streamer_playing_rust(streamer_username):
    # This is where you would check if the streamer is playing "Rust".
    # The following logic assumes `TwitchChannelPointsMiner` or a similar mechanism can be used to fetch stream status.
    # Assuming `get_streamer_game()` method or similar exists in the current code base

    # You need to either check the game's name through the API or infer it by stream status
    streamer = Streamer(streamer_username)
    if streamer.game == "Rust":
        return True
    return False

# Function to initialize the TwitchMiner
def start_twitch_miner(username, file_path):
    streamers_list = load_streamers_from_file(file_path)
    eligible_streamers = []

    # Filter streamers who are playing "Rust"
    for streamer_username in streamers_list:
        if is_streamer_playing_rust(streamer_username):
            eligible_streamers.append(Streamer(streamer_username))
    
    if not eligible_streamers:
        print("No streamers found who are playing Rust.")
        return

    # Initialize the TwitchChannelPointsMiner with relevant settings
    twitch_miner = TwitchChannelPointsMiner(
        username=username,
        password="write-your-secure-psw",  # Secure your password input method
        claim_drops_startup=False,         # If you want to auto-claim all drops
        priority=[Priority.STREAK, Priority.DROPS, Priority.ORDER],
        logger_settings=LoggerSettings(
            save=True,
            console_level=logging.INFO,
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
                events=[Events.STREAMER_ONLINE, Events.STREAMER_OFFLINE, "BET_LOSE"],
                disable_notification=True
            ),
            discord=Discord(
                webhook_api="https://discord.com/api/webhooks/0123456789/0a1B2c3D4e5F6g7H8i9J",
                events=[Events.STREAMER_ONLINE, Events.STREAMER_OFFLINE, Events.BET_LOSE]
            )
        ),
        streamer_settings=StreamerSettings(
            make_predictions=True,
            follow_raid=True,
            claim_drops=True,
            watch_streak=True,
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
    
    # Start mining with the eligible streamers
    twitch_miner.mine(eligible_streamers)

# Main Program
if __name__ == "__main__":
    # Prompt the user for their username and the file containing the streamer list
    username = input("Enter your Twitch username: ")
    file_path = input("Enter the path to your streamer list file: ")
    
    if os.path.exists(file_path):
        start_twitch_miner(username, file_path)
    else:
        print("Streamer list file not found.")

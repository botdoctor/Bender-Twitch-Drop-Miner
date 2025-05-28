Based on https://github.com/rdavydov/Twitch-Channel-Points-Miner-v2.

This is the working version of the twitch miner. It will mine for twitch drops succesfully and also rack up points. It will claim these drops and can handle many accounts working.


The way this script works is you create a .txt file with the name of all the streamers who are dropping. You then run final.py login to the account of your choosing. Then select the .txt file you want to take all the streamers from. It will work its way down this list until it has grabbed all the drops. Put the most important drops and most important streamers near the top of the list since if a streamer is dropping drops, the backup is to rank them by where they appear in the .txt file.

# Simple Birthday Bot
A simple and open-source birthday bot for Discord.

Current version is `0.1.0`.

# Setting up the bot
## Steps
1. Download and install Python 3.12
2. Clone and cd into this repository
3. Download dependencies via `python -m pip install -r requirements.txt` (or your system's equivalent)
4. CD into the directory `data`.
5. Make a new file called `config.ini`.
6. Add the following lines into the file: 
```ini
[GENERAL]
token=YOUR TOKEN
```
7. Replace "YOUR TOKEN" with your bots token.
8. Cd back into the repository root and run `python main.py` (or your system's equivalent)

## Additional
Feel free to peer into the `data/example_config.ini` file for all of the currently available configurations.

You can also specify custom paths for both the database and configuration file via the `main.py` file. The variables are
`DATABASE_FILEPATH` and `CONFIG_FILEPATH`. Ensure that these filepaths matches their respective files. 

# Limitations
This bot is not intended to be constantly updated with new features. If you do have a feature request, then do not fear
to open a new issue for it. However, do not expect the feature to be added within a short timeframe.

That doesn't mean that bugs will go unfixed though. Unless a bug/glitch cannot be reproduced, then said bug/glitch will
be fixed as soon as possible.
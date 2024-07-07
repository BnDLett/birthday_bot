from time import time
from interactions import (
    slash_command,
    Client,
    slash_option,
    SlashContext,
    OptionType,
    Intents,
    Task,
    IntervalTrigger,
    GuildText,
    User,
    Embed,
    Message,
    Permissions,
    EmbedFooter,
    Color,
)
from pathlib import Path
from datetime import datetime
from itertools import islice
import hell
import sqlite3
import configparser

# I promise that I am not a worshiper of the devil.
hell.consume_mankind()

# Constants
DATABASE_FILEPATH = Path('data/database.db')
CONFIG_FILEPATH = Path('data/config.ini')

# bot
bot = Client(intents=Intents.DEFAULT)

# Error checking
if not DATABASE_FILEPATH.parent.exists():
    raise FileNotFoundError('Could not find database parent folder. Please ensure that it exists.')
elif not CONFIG_FILEPATH.exists():
    raise FileNotFoundError('Could not find configuration file. Please ensure that it exists and that it is configured'
                            ' properly.')

# Database
database = sqlite3.connect(DATABASE_FILEPATH)
cursor = database.cursor()

cursor.execute(
    'CREATE TABLE IF NOT EXISTS server_list ('
    'id         INT NOT NULL, '
    'channel_id INT NOT NULL  '
    ');'
)

cursor.execute(
    'CREATE TABLE IF NOT EXISTS birthday_list ('
    'user_id             INT PRIMARY KEY NOT NULL, '
    'server_id           INT             NOT NULL, '
    'year                INT,                          '
    'month               INT             NOT NULL, '
    'day                 INT             NOT NULL, '
    'last_year_notified  INT             NOT NULL, '
    'FOREIGN KEY (server_id) REFERENCES server(id)     '
    ');'
)

database.commit()

# Configuration and configuration error checking.
# config = json.load(CONFIG_FILEPATH.open())
# TOKEN: str = config.get('token', None)
# DEBUG_ENABLED: bool = config.get('debug_mode', False)
# DEBUG_SCOPE: int | str = config.get('debug_server_id', None)
# CHECK_INTERVAL: int = config.get('check_interval', 30)

config = configparser.ConfigParser()
config.read(CONFIG_FILEPATH)

TOKEN = config.get('GENERAL', 'token')
CHECK_INTERVAL = config.getint('GENERAL', 'check_interval', fallback=30)

DEBUG_ENABLED = config.getboolean('DEBUG', 'debug_enabled', fallback=False)
DEBUG_SCOPE = config.getint('DEBUG', 'debug_server_id', fallback=None)

EMBED_COLOR = Color(config.get('EMBEDS', 'color', fallback='#FF2400'))

if DEBUG_ENABLED and DEBUG_SCOPE is None:
    raise ValueError("Debug mode is enabled but an ID for a debug server was not found. Please specify the ID of the"
                     "debug server before you use debug mode.")
elif DEBUG_ENABLED:
    bot.debug_scope = DEBUG_SCOPE


# General functions
async def run_birthday(channel: GuildText, lucky_user: User):
    birthday_embed = Embed(
        title="It's someone's lucky day!",
        description=f"Happy birthday, {lucky_user.mention}!",
        color=EMBED_COLOR
    )
    await channel.send(embed=birthday_embed)


@Task.create(IntervalTrigger(minutes=CHECK_INTERVAL))
async def check_birthdays():
    current = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    cursor.execute('SELECT * FROM birthday_list WHERE last_year_notified < ?', (current.year,))
    birthdays = cursor.fetchall()

    for birthday in birthdays:
        user_id: int = birthday[0]
        server_id: int = birthday[1]
        # year: int = birthday[2]
        month: int = birthday[3]
        day: int = birthday[4]

        next_run = datetime.strptime(f'{str(current.year).ljust(4, '0')}-{month}-{day}', '%Y-%m-%d')

        cursor.execute('SELECT * FROM server_list WHERE id == ?', (server_id,))
        server = cursor.fetchone()
        channel_id = server[1]

        user: User = bot.get_user(user_id)
        channel: GuildText = bot.get_channel(channel_id)

        if next_run != current:
            continue

        await run_birthday(channel, user)

        cursor.execute('UPDATE birthday_list SET last_year_notified = ? WHERE user_id == ?', (current.year, user_id))

    database.commit()


async def end_signup(start: float, msg: Message):
    end = time()

    await msg.edit(content=f'Signed you up in {((end - start) * 1000):.2f} milliseconds!')


async def server_in_db(ctx: SlashContext, server_id_tuple: tuple[str], send_message: bool = True) -> bool:
    cursor.execute('SELECT * FROM server_list WHERE ? == id', server_id_tuple)
    server_in_database = cursor.fetchone()

    if server_in_database is None:
        if send_message:
            await ctx.send("This server is not currently registered in the database.")
        return False

    return True


# Events 🗿
@bot.listen()
async def on_ready():
    print(f"The bot is ready. Current latency: {bot.latency}")
    await check_birthdays()
    check_birthdays.start()


# Commands
@slash_command(
    name='register-server',
    description='Register the server into the bot\'s database.',
)
@slash_option(
    name='channel_id',
    description='The ID of the birthday channel.',
    opt_type=OptionType.STRING,
    required=True
)
async def setup(ctx: SlashContext, channel_id: str):
    if not ctx.author.has_permission(Permissions.MANAGE_CHANNELS):
        await ctx.send("You do not have permission to run this command! Please make sure that you contact someone with"
                       "the \"manage channels\" permission in order to run this command for you. ")
        return

    msg = await ctx.send("Registering the server into the database.")

    start = time()

    server_id = str(ctx.guild.id)
    server_id_tuple = (server_id,)

    if await server_in_db(ctx, server_id_tuple, False):
        return

    cursor.execute('INSERT INTO server_list (id, channel_id) VALUES (?, ?)', (server_id, channel_id))
    database.commit()

    end = time()
    await msg.edit(content=f'Registered the server in {((end - start) * 1000):.2f} milliseconds.')


@slash_command(
    name="signup",
    description="Signup for the bot."
)
@slash_option(
    name="day",
    opt_type=OptionType.NUMBER,
    description="The day of your birthday.",
    required=True
)
@slash_option(
    name="month",
    opt_type=OptionType.NUMBER,
    description="The month of your birthday.",
    required=True
)
@slash_option(
    name="year",
    opt_type=OptionType.NUMBER,
    description="The year of your birthday. Not required.",
)
async def signup(ctx: SlashContext, day: int, month: int, year: int = None):
    msg = await ctx.send("Signing you up!")

    start = time()

    day_range = range(1, 31)
    month_range = range(1, 12)

    if month not in month_range or day not in day_range:
        await msg.edit(content='The dates that you provided are not valid dates. Please double check them and run the'
                               'command again with the proper dates.')
        return

    current = datetime.now()
    server_id_tuple = (str(ctx.guild.id),)

    if not await server_in_db(ctx, server_id_tuple):
        return

    cursor.execute('SELECT * FROM birthday_list WHERE ? == user_id', (str(ctx.user.id),))
    user_in_database = cursor.fetchone()
    if user_in_database is not None:
        await end_signup(start, msg)
        database.commit()
        return

    cursor.execute(
        'INSERT INTO birthday_list ('
        'user_id, '
        'server_id, '
        'year, '
        'month, '
        'day, '
        'last_year_notified'
        ') VALUES (?, ?, ?, ?, ?, ?)',
        (str(ctx.user.id), str(ctx.guild.id), year, month, day, (current.year - 1))
    )
    database.commit()

    await end_signup(start, msg)


@slash_command(
    name='list',
    description='List the birthdays of the individuals in this server.'
)
@slash_option(
    name='page',
    description='The page number of the list.',
    opt_type=OptionType.INTEGER,
    required=True
)
async def list_birthdays(ctx: SlashContext, page: int):
    server_id_str = str(ctx.guild.id)
    server_id_tuple = (server_id_str,)

    page -= 1
    start_slice = page * 15
    end_slice = start_slice + 15

    birthdays_in_page = []
    page_str = 'USER - YYYY/MM/DD\n\n'

    if not await server_in_db(ctx, server_id_tuple):
        return

    cursor.execute('SELECT * FROM birthday_list WHERE ? == server_id', server_id_tuple)
    birthday_list = cursor.fetchall()

    if len(birthday_list) == 0:
        embed_footer = EmbedFooter('Perhaps you could start by adding your own?')
        no_birthdays_embed = Embed(
            title='No birthdays found.',
            description='No birthdays were found.',
            footer=embed_footer,
            color=EMBED_COLOR
        )

        await ctx.send(embed=no_birthdays_embed)
        return

    elif len(birthday_list) < (start_slice + 1):
        embed_footer = EmbedFooter('Perhaps you could try a smaller page number?')
        page_not_exist_embed = Embed(
            title='Page not found',
            description='The page that you specified does not exist.',
            footer=embed_footer,
            color=EMBED_COLOR
        )

        await ctx.send(embed=page_not_exist_embed)
        return

    for birthday in islice(birthday_list, start_slice, end_slice):
        birthdays_in_page.append(birthday)

    page_str += ''.join(f'<@{user_id}> - {year}/{str(month).rjust(2, '0')}/'
                        f'{str(day).rjust(2, '0')}' for user_id, _, year, month, day, _ in birthday_list)

    list_embed = Embed(
        title="Birthday list",
        description=page_str,
        color=EMBED_COLOR
    )
    await ctx.send(embed=list_embed)


# Start bot (duh)
if __name__ == "__main__":
    try:
        bot.start(token=TOKEN)
    finally:
        database.close()

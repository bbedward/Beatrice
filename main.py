import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio
import datetime

import api
import settings
import db
import util
import paginator

logger = util.get_logger("main")

BOT_VERSION = "0.1"

# Spam Threshold (Seconds) - how long to output certain commands (e.g. price)
SPAM_THRESHOLD=60
# Change command prefix to whatever you want to begin commands with
COMMAND_PREFIX=settings.command_prefix

# HELP menu header
AUTHOR_HEADER="Beatrice v{0} (NANO Utility Bot)".format(BOT_VERSION)

# Command DOC (TRIGGER, CMD, Overview, Info)
'''
CMD: Command trigger
INFO: Command usage
'''

### Commands for everyone
PRICE = {
		"CMD"      : "{0}price".format(COMMAND_PREFIX),
        "INFO"     : "Display NANO price information from a few of the top exchanges"
}

MEME = {
		"CMD"      : "{0}meme".format(COMMAND_PREFIX),
        "INFO"     : "Display next meme in sequence"
}

MEMELIST = {
		"CMD"      : "{0}memelist".format(COMMAND_PREFIX),
        "INFO"     : "Receive private message with a list of all memes stored with the bot"
}

PUP = {
        "CMD"      : "{0}pup".format(COMMAND_PREFIX),
        "INFO"     : "Display next pup in sequence"
}

PUPLIST = {
		"CMD"      : "{0}puplist".format(COMMAND_PREFIX),
        "INFO"     : "Receive private message with a list of all pups stored with the bot"
}

MEOW = {
		"CMD"      : "{0}meow".format(COMMAND_PREFIX),
        "INFO"     : "Display next meow in sequence"
}

MEOWLIST = {
		"CMD"      : "{0}meowlist".format(COMMAND_PREFIX),
        "INFO"     : "Receive private message with a list of all meows stored with the bot"
}

### Admin commands
ADDPUP = {
		"CMD"      : "{0}addpup, takes: url, author, title".format(COMMAND_PREFIX),
        "INFO"     : "Add URL to the bot's pup list",
        "USAGE"    : "{0}addpup <url> <author> <title>".format(COMMAND_PREFIX)
}

ADDMEME = {
   		"CMD"      : "{0}addmeme, takes: url, author, title".format(COMMAND_PREFIX),
        "INFO"     : "Add URL to the bot's meme list",
        "USAGE"    : "{0}addmeme <url> <author> <title>".format(COMMAND_PREFIX)
}

ADDMEOW = {
   		"CMD"      : "{0}addmeow, takes: url, author, title".format(COMMAND_PREFIX),
        "INFO"     : "Add URL to the bot's meow list",
        "USAGE"    : "{0}addmeow <url> <author> <title>".format(COMMAND_PREFIX)
}

REMOVEPUP = {
   		"CMD"      : "{0}removepup, takes: url or id".format(COMMAND_PREFIX),
        "INFO"     : "Remove pup matching URL or ID from the bot's pup list" 
}

REMOVEMEME = {
   		"CMD"      : "{0}removememe, takes: url or id".format(COMMAND_PREFIX),
        "INFO"     : "Remove meme matching URL or ID from the bot's meme list" 
}

REMOVEMEOW = {
   		"CMD"      : "{0}removemeow, takes: url or id".format(COMMAND_PREFIX),
        "INFO"     : "Remove meow matching URL or ID from the bot's meow list" 
}

### Dictionary of different command categories
COMMANDS = {
		"USER_COMMANDS"          : [PRICE, MEME, MEMELIST, PUP, PUPLIST, MEOW, MEOWLIST],
        "ADMIN_COMMANDS"         : [ADDPUP, ADDMEME, ADDMEOW, REMOVEPUP, REMOVEMEME, REMOVEMEOW],
}

# Create discord client
client = Bot(command_prefix=COMMAND_PREFIX)
client.remove_command('help')

# Don't make them wait when bot first launches
initial_ts=datetime.datetime.now() - datetime.timedelta(seconds=SPAM_THRESHOLD)
last_price = {}
last_meme = {}
last_pup = {}
last_meow = {}
def create_spam_dicts():
    """map every channel the client can see to datetime objects
        this way we can have channel-specific spam prevention"""
    global last_price
    global last_meme
    global last_pup
    global last_meow
    for c in client.get_all_channels():
        if not is_private(c):
            last_price[c.id] = initial_ts
            last_meme[c.id] = initial_ts
            last_pup[c.id] = initial_ts
            last_meow[c.id] = initial_ts

@client.event
async def on_ready():
    logger.info("Beatrice v%s started", BOT_VERSION)
    logger.info("Discord.py API version %s", discord.__version__)
    logger.info("Name: %s", client.user.name)
    logger.info("ID: %s", client.user.id)
    create_spam_dicts()
    await client.change_presence(activity=discord.Game(settings.playing_status))

def is_private(channel):
    """Check if a discord channel is private"""
    return isinstance(channel, discord.abc.PrivateChannel)

def has_admin_role(roles):
    """Check if user has an admin role defined in our settings"""

    for r in roles:
        if r.name in settings.admin_roles:
            return True
    return False

def is_admin(user):
    """Returns true if user is an admin"""
    if str(user.id) in settings.admin_ids:
        return True
    for m in client.get_all_members():
        if m.id == user.id:
            if has_admin_role(m.roles):
                return True
    return False

def valid_url(url):
    # TODO we should check content-type header with aiohttp
    return True

### Public Commands

@client.command()
async def commandlist(ctx):
    message = ctx.message
    embed = discord.Embed(colour=discord.Colour.magenta())
    embed.title = "Commands"
    for cmd in COMMANDS["USER_COMMANDS"]:
        embed.add_field(name=cmd['CMD'], value=cmd['INFO'], inline=False)
    if is_admin(message.author):
        for cmd in COMMANDS["ADMIN_COMMANDS"]:
            embed.add_field(name=cmd['CMD'], value=cmd['INFO'], inline=False)
    await message.author.send(embed=embed)

@client.command()
async def price(ctx):
    message = ctx.message
    if is_private(message.channel):
        return
	# Check spam
    global last_price
    if message.channel.id not in last_price:
        last_price[message.channel.id] = datetime.datetime.now()
    tdelta = datetime.datetime.now() - last_price[message.channel.id]
    if SPAM_THRESHOLD > tdelta.seconds:
        await post_response(message, "No more price for {0} seconds", (SPAM_THRESHOLD - tdelta.seconds))
        return
    last_price[message.channel.id] = datetime.datetime.now()
    msg = await message.channel.send("Retrieving latest prices...")
    embed = discord.Embed(colour=discord.Colour.green())
    embed.title = "Current NANO Prices"
    prices = await api.get_all_prices()
    pricestr = "{0:.8f} BTC"
    for exchange, price in prices:
         embed.add_field(name=exchange, value=pricestr.format(price))
    cmc = await api.get_cmc_data()
    if cmc is not None:
        embed.description = cmc
    await msg.edit(content="", embed=embed)

@client.command()
async def meme(ctx):
    message = ctx.message
    if is_private(message.channel):
        return
    elif message.channel.id in settings.no_spam_channels:
        return
	# Check spam
    global last_meme
    if message.channel.id not in last_meme:
        last_meme[message.channel.id] = datetime.datetime.now()
    tdelta = datetime.datetime.now() - last_meme[message.channel.id]
    if SPAM_THRESHOLD > tdelta.seconds:
        await post_response(message, "No more memes for {0} seconds", (SPAM_THRESHOLD - tdelta.seconds))
        return
    last_meme[message.channel.id] = datetime.datetime.now()
    meme = db.get_next_meme()
    if meme is None:
        await post_response(message, "There are no memes! Add some with !addmeme")
        return
    embed = discord.Embed(colour=discord.Colour.purple())
    embed.title = "Meme #{0} - ${1}".format(meme['id'], meme['title'])
    embed.set_author(meme['author'])
    embed.set_image(url=meme['url'])
    await message.channel.send(embed=embed)

@client.command(aliases=["memes"])
async def memelist(ctx):
    message = ctx.message
    memes = db.get_memes()
    if len(memes) == 0:
        embed = discord.Embed(colour=discord.Colour.red())
        embed.title="No Memes"
        embed.description="There no memes. Add memes with `{0}addmeme`".format(COMMAND_PREFIX)
        await message.author.send(embed=embed)
        return
    title="Meme List"
    description=("Here are all the memes!")
    entries = []
    for meme in memes:
        entries.append(paginator.Entry(str(meme['id']),meme['url']))

    # Do paginator for favorites > 10
    if len(entries) > 10:
        pages = paginator.Paginator.format_pages(entries=entries,title=title,description=description)
        p = paginator.Paginator(client,message=message,page_list=pages,as_dm=True)
        await p.paginate(start_page=1)
    else:
        embed = discord.Embed(colour=discord.Colour.teal())
        embed.title = title
        embed.description = description
        for e in entries:
            embed.add_field(name=e.name,value=e.value,inline=False)
    await message.author.send(embed=embed)

@client.command()
async def meow(ctx):
    message = ctx.message
    if is_private(message.channel):
        return
    elif message.channel.id in settings.no_spam_channels:
        return
	# Check spam
    global last_meow
    if message.channel.id not in last_meow:
        last_meow[message.channel.id] = datetime.datetime.now()
    tdelta = datetime.datetime.now() - last_meow[message.channel.id]
    if SPAM_THRESHOLD > tdelta.seconds:
        await post_response(message, "No more meows for {0} seconds", (SPAM_THRESHOLD - tdelta.seconds))
        return
    last_meow[message.channel.id] = datetime.datetime.now()
    meow = db.get_next_meow()
    if meow is None:
        await post_response(message, "There are no meows! Add some with !addmeow")
        return
    embed = discord.Embed(colour=discord.Colour.purple())
    embed.title = "Meow #{0} - ${1}".format(meow['id'], meow['title'])
    embed.set_author(meow['author'])
    embed.set_image(url=meow['url'])
    await message.channel.send(embed=embed)

@client.command(aliases=["meows"])
async def meowlist(ctx):
    message = ctx.message
    meows = db.get_meows()
    if len(meows) == 0:
        embed = discord.Embed(colour=discord.Colour.red())
        embed.title="No Meows"
        embed.description="There no meows. Add meows with `{0}addmeow`".format(COMMAND_PREFIX)
        await message.author.send(embed=embed)
        return
    title="Meow List"
    description=("Here are all the meows!")
    entries = []
    for meow in meows:
        entries.append(paginator.Entry(str(meow['id']),meow['url']))

    # Do paginator for favorites > 10
    if len(entries) > 10:
        pages = paginator.Paginator.format_pages(entries=entries,title=title,description=description)
        p = paginator.Paginator(client,message=message,page_list=pages,as_dm=True)
        await p.paginate(start_page=1)
    else:
        embed = discord.Embed(colour=discord.Colour.teal())
        embed.title = title
        embed.description = description
        for e in entries:
            embed.add_field(name=e.name,value=e.value,inline=False)
    await message.author.send(embed=embed)

@client.command()
async def pup(ctx):
    message = ctx.message
    if is_private(message.channel):
        return
    elif message.channel.id in settings.no_spam_channels:
        return
	# Check spam
    global last_pup
    if message.channel.id not in last_pup:
        last_pup[message.channel.id] = datetime.datetime.now()
    tdelta = datetime.datetime.now() - last_pup[message.channel.id]
    if SPAM_THRESHOLD > tdelta.seconds:
        await post_response(message, "No more memes for {0} seconds", (SPAM_THRESHOLD - tdelta.seconds))
        return
    last_pup[message.channel.id] = datetime.datetime.now()
    pup = db.get_next_pup()
    if pup is None:
        await post_response(message, "There are no pups! Add some with !addpup")
        return
    embed = discord.Embed(colour=discord.Colour.purple())
    embed.title = "Pup #{0} - ${1}".format(pup['id'], pup['title'])
    embed.set_author(pup['author'])
    embed.set_image(url=pup['url'])
    await message.channel.send(embed=embed)

@client.command(aliases=["pups"])
async def puplist(ctx):
    message = ctx.message
    pups = db.get_pups()
    if len(pups) == 0:
        embed = discord.Embed(colour=discord.Colour.red())
        embed.title="No Pups"
        embed.description="There no pups. Add pups with `{0}addpup`".format(COMMAND_PREFIX)
        await message.author.send(embed=embed)
        return
    title="Pup List"
    description=("Here are all the pups!")
    entries = []
    for pup in pups:
        entries.append(paginator.Entry(str(pup['id']),pup['url']))

    # Do paginator for favorites > 10
    if len(entries) > 10:
        pages = paginator.Paginator.format_pages(entries=entries,title=title,description=description)
        p = paginator.Paginator(client,message=message,page_list=pages,as_dm=True)
        await p.paginate(start_page=1)
    else:
        embed = discord.Embed(colour=discord.Colour.teal())
        embed.title = title
        embed.description = description
        for e in entries:
            embed.add_field(name=e.name,value=e.value,inline=False)
    await message.author.send(embed=embed)

### Admin Commands

@client.command()
async def addmeme(ctx, url: str = None, author: str = None, title: str = None):
    message = ctx.message
    if not is_admin(message.author):
        return
    elif url is None or author is None or title is None:
        await post_usage(message, ADDMEME)
    elif not valid_url(url):
        await message.author.send("Invalid URL. Valid urls begin with http:// or https://")
    elif db.add_meme(url, author, title):
        await message.author.send("Meme added: {0}".format(title))
    else:
        await message.author.send("Could not add meme {0}. It may already exist".format(url))
    
@client.command()
async def removememe(ctx, id: str):
    message = ctx.message
    if not is_admin(message.author):
        return
    elif db.remove_meme(id):
        await message.author.send("Meme {0} removed".format(id))
    else:
        await message.author.send("Could not remove meme {0}. It may not exist".format(id))

@client.command()
async def addpup(ctx, url: str = None, author: str = None, title: str = None):
    message = ctx.message
    if not is_admin(message.author):
        return
    elif url is None or author is None or title is None:
        await post_usage(message, ADDPUP)
    elif not valid_url(url):
        await message.author.send("Invalid URL. Valid urls begin with http:// or https://")
    elif db.add_pup(url, author, title):
        await message.author.send("Pup added: {0}".format(title))
    else:
        await message.author.send("Could not add Pup {0}. It may already exist".format(url))
    
@client.command()
async def removepup(ctx, id: str):
    message = ctx.message
    if not is_admin(message.author):
        return
    elif db.remove_pup(id):
        await message.author.send("Pup {0} removed".format(id))
    else:
        await message.author.send("Could not Remove pup {0}. It may not exist".format(id))

@client.command()
async def addmeow(ctx, url: str = None, author: str = None, title: str = None):
    message = ctx.message
    if not is_admin(message.author):
        return
    elif url is None or author is None or title is None:
        await post_usage(message, ADDMEOW)
    elif not valid_url(url):
        await message.author.send("Invalid URL. Valid urls begin with http:// or https://")
    elif db.add_meow(url, author, title):
        await message.author.send("Meow added: {0}".format(title))
    else:
        await message.author.send("Could not add meow {0}. It may already exist".format(url))
    
@client.command()
async def removemeow(ctx, id: str):
    message = ctx.message
    if not is_admin(message.author):
        return
    elif db.remove_meow(id):
        await message.author.send("Meow {0} removed".format(id))
    else:
        await message.author.send("Could not remove meow {0}. It may not exist".format(id))

### Re-Used Discord Functions
async def post_response(message, template, *args):
    response = template.format(*args)
    if not is_private(message.channel):
        response = "<@" + str(message.author.id) + "> \n" + response
    logger.info("sending response: '%s' for message: '%s' to userid: '%s' name: '%s'", response, message.content, message.author.id, message.author.name)
    asyncio.sleep(0.05) # Slight delay to avoid discord bot responding above commands
    return await message.channel.send(response)

async def post_usage(message, command):
    embed = discord.Embed(colour=discord.Colour.purple())
    embed.title = "Usage:"
    embed.add_field(name=command['CMD'], value=command['USAGE'],inline=False)
    await message.author.send(embed=embed)

# Start the bot
client.run(settings.discord_bot_token)

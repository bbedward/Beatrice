import discord
from discord.ext import commands, tasks
from discord.ext.commands import Bot
import asyncio
import datetime
import re

import api
import settings
import db
import util
import paginator

intents = discord.Intents.default()
intents.members = True
intents.presences = True

SUPERS=[303599885800964097]

logger = util.get_logger("discord")

BOT_VERSION = "1.0"

# Spam Threshold (Seconds) - how long to output certain commands (e.g. price)
SPAM_THRESHOLD=300
# Change command prefix to whatever you want to begin commands with
COMMAND_PREFIX=settings.command_prefix

# HELP menu header
AUTHOR_HEADER="Beatrice v{0} (BA/NANO Utility Bot)".format(BOT_VERSION)

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

FRIDGE = {
		"CMD"      : "{0}fridge".format(COMMAND_PREFIX),
        "INFO"     : "Display next fridge in sequence"
}

FRIDGELIST = {
		"CMD"      : "{0}fridgelist".format(COMMAND_PREFIX),
        "INFO"     : "Receive private message with a list of all fridges stored with the bot"
}

FODL = {
		"CMD"      : "{0}fodl".format(COMMAND_PREFIX),
        "INFO"     : "Verifies Folding@Home Bananominer Client configuration after completing 1 Work Unit in banano-mining channel"
}
FARMS = {
		"CMD"      : "{0}farms".format(COMMAND_PREFIX),
        "INFO"     : "Fetches current TVL and APR for all active wrapped banano farms"
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

ADDFRIDGE = {
   		"CMD"      : "{0}addfridge, takes: url, author, title".format(COMMAND_PREFIX),
        "INFO"     : "Add URL to the bot's fridge list",
        "USAGE"    : "{0}addfridge <url> <author> <title>".format(COMMAND_PREFIX)
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

REMOVEFRIDGE = {
   		"CMD"      : "{0}removefridge, takes: url or id".format(COMMAND_PREFIX),
        "INFO"     : "Remove fridge matching URL or ID from the bot's fridge list"
}

MUTE = {
   		"CMD"      : "{0}mute or {0}muzzle, takes: user ID(s) or user mention, duration (optional)".format(COMMAND_PREFIX),
        "INFO"     : "mute @bbedward 60 = mute bbedward for 60 minutes"
}

UNMUTE = {
   		"CMD"      : "{0}unmute or {0}unmuzzle, user ID(s) or user mention".format(COMMAND_PREFIX),
        "INFO"     : "Unmute mentioned user(s)"
}

NOIMAGES = {
   		"CMD"      : "{0}noimages, user ID(s) or user mention".format(COMMAND_PREFIX),
        "INFO"     : "Stops user posting images"
}

ALLOWIMAGES = {
   		"CMD"      : "{0}allowimages, user ID(s) or user mention".format(COMMAND_PREFIX),
        "INFO"     : "Allows user to post images"
}

KICK = {
        "CMD"       : "{0}kick, takes: user ID(s) or user mention, reason (optional)".format(COMMAND_PREFIX),
        "INFO"      : "kick 397868283870707713 303599885800964097 reason='You Suck' = kick user 303599885800964097 and user 397868283870707713"
}

BAN = {
        "CMD"       : "{0}ban, takes: user ID(s) or user mention, reason (optional))".format(COMMAND_PREFIX),
        "INFO"      : "kick 397868283870707713 303599885800964097 = kick user 303599885800964097 and user 397868283870707713"
}

### Dictionary of different command categories
COMMANDS = {
		"USER_COMMANDS"          : [PRICE, MEME, MEMELIST, PUP, PUPLIST, MEOW, MEOWLIST, FRIDGE, FRIDGELIST, FODL, FARMS],
        "ADMIN_COMMANDS"         : [ADDPUP, ADDMEME, ADDMEOW, ADDFRIDGE, REMOVEPUP, REMOVEMEME, REMOVEMEOW, REMOVEFRIDGE, MUTE, UNMUTE, KICK, BAN],
}

# Create discord client
client = Bot(command_prefix=COMMAND_PREFIX, intents=intents)
client.remove_command('help')

# Don't make them wait when bot first launches
initial_ts=datetime.datetime.now() - datetime.timedelta(seconds=SPAM_THRESHOLD)
last_price = {}
last_meme = {}
last_pup = {}
last_meow = {}
last_fridge = {}
last_fodl = {}
last_farms = {}
def create_spam_dicts():
    """map every channel the client can see to datetime objects
        this way we can have channel-specific spam prevention"""
    global last_price
    global last_meme
    global last_pup
    global last_meow
    global last_fridge
    global last_fodl
    global last_farms
    for c in client.get_all_channels():
        if not is_private(c):
            last_price[c.id] = initial_ts
            last_meme[c.id] = initial_ts
            last_pup[c.id] = initial_ts
            last_meow[c.id] = initial_ts
            last_fridge[c.id] = initial_ts
            last_fodl[c.id] = initial_ts
            last_farms[c.id] = initial_ts

@client.event
async def on_ready():
    logger.info("Beatrice v%s started", BOT_VERSION)
    logger.info("Discord.py API version %s", discord.__version__)
    logger.info("Name: %s", client.user.name)
    logger.info("ID: %s", client.user.id)
    create_spam_dicts()
    await client.change_presence(activity=discord.Game(settings.playing_status))
    asyncio.get_event_loop().create_task(unsilence_users())
    update_sidebar_status.start() #start the update_sidebar_status() loop

# Store the last unit the status is displayed as
status_unit = None

# Periodic task to update activity status to price (in sats and USD)
@tasks.loop(seconds=10.0)
async def update_sidebar_status():
    global status_unit
    banano = await api.get_status()
    if banano is not None:
        if status_unit == 'nano':
            await client.change_presence(activity=discord.Game(f"{banano['satoshi']:.1f} sats"))
            status_unit = 'ban'
        else:
            await client.change_presence(activity=discord.Game(f"${banano['usdprice']:.4f}"))
            status_unit = 'nano'
    else:
         await client.change_presence(activity=discord.Game(f"Error checking prices"))

@client.event
async def on_member_join(member):
	if db.silenced(member.id):
		muzzled = member.guild.get_role(settings.muzzled_role)
		await member.add_roles(muzzled)

@client.event
async def on_reaction_add(reaction, user):
	if reaction.emoji == '\u274C' and reaction.count >= 5 and reaction.message.channel.id == 585626036574748684:
		await reaction.message.delete()

# Periodic check job to unsilence users
async def unsilence_users():
	try:
		await asyncio.sleep(10)
		asyncio.get_event_loop().create_task(unsilence_users())
		for s in db.get_silenced():
			if s.expiration is None:
				continue
			elif datetime.datetime.now() >= s.expiration:
				for guild in client.guilds:
					if guild.id == s.server_id:
						muzzled = guild.get_role(settings.muzzled_role)
						for member in guild.members:
							if member.id == int(s.user_id):
								await member.remove_roles(muzzled)
								break
				db.unsilence(s.user_id)
	except Exception as ex:
		logger.exception(ex)

def is_private(channel):
    """Check if a discord channel is private"""
    return isinstance(channel, discord.abc.PrivateChannel)

def has_admin_role(roles):
    """Check if user has an admin role defined in our settings"""

    for r in roles:
        if r.id in settings.admin_roles:
            return True
    return False

def is_admin(member):
    """Returns true if user is an admin"""
    if str(member.id) in settings.admin_ids:
        return True
    elif has_admin_role(member.roles):
        return True
    return False

def is_bannable(user):
    """Returns true if user does not have any special roles"""
    if str(user.id) in settings.admin_ids:
        return False
    for m in client.get_all_members():
        if m.id == user.id:
            for role in m.roles:
                if role.name.lower() not in ['banano jail', 'muzzled', '@everyone', 'citizens', 'troll', 'Private ^', 'Corporal ^^', 'Sergeant ^^^', 'Officer -', 'Second Lieutenant |', 'First Lieutenant ||', 'Captain *', 'Colonel  **', 'General ***']:
                    return False
    return True

def valid_url(url):
    # TODO we should check content-type header with aiohttp
    return True

### Public Commands

@client.command(aliases=["help"])
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
    if message.author.id not in SUPERS:
        if SPAM_THRESHOLD > tdelta.seconds:
            await message.author.send("No more price for {0} seconds".format(SPAM_THRESHOLD - tdelta.seconds))
            return
        last_price[message.channel.id] = datetime.datetime.now()
    msg = await message.channel.send("Retrieving latest prices...")
    embed = discord.Embed(colour=discord.Colour.green())
    embed.title = "Current Prices"
    btc = None
    nano = None
    banano = None
    prices = await api.get_all_prices()
    for item, price in prices:
        if item == 'BTC':
            btc = price
        elif item == 'NANO':
            nano = price
        elif item == 'BANANO':
            banano = price
    # Display data
    banpernan = ""
    embed.description = ''
    embed.description += '**BANANO**'
    if banano is None:
        embed.description += '\nCurrently Unavailable\n'
    else:
        if banano['change'] < 0:
            embed.colour=discord.Colour.red()
        embed.description += "```"
        embed.description += f"Rank            : #{banano['rank']}\n"
        if nano is not None:
            ban_in_nano = banano['usdprice'] / nano['usdprice']
            banpernan = 1 / ban_in_nano
            embed.description += f"Price  (NANO)   : {ban_in_nano:.6f} NANO\n"
        embed.description += f"Price  (BTC)    : {banano['satoshi']:.1f} sats\n"
        embed.description += f"Price  (USD)    : ${banano['usdprice']:.6f}\n"
        if settings.VESPRICE and 'bolivar' in banano:
            embed.description += f"Price  (VES)    : {banano['bolivar']:.2f} Bs.S\n"
        embed.description += f"Volume (24H)    : {banano['volume']:,.2f} BTC\n"
        embed.description += f"Market Cap      : ${int(banano['mcap']):,}\n"
        embed.description += "```"
    embed.description += "\n**NANO**"
    if nano is None:
        embed.description += '\nCurrently Unavailable\n'
    else:
        banpernan = nano['usdprice'] / banano['usdprice']
        embed.description += "```"
        embed.description += f"Rank            : #{nano['rank']}\n"
        embed.description += f"Price  (BTC)    : {nano['btcprice']:.8f} BTC\n"
        embed.description += f"Price  (USD)    : ${nano['usdprice']:.2f}\n"
        if settings.VESPRICE and 'bolivar' in nano:
            embed.description += f"Price  (VES)    : {nano['bolivar']:.2f} Bs.S\n"
        embed.description += f"Volume (24H)    : {nano['volume']:,.2f} BTC\n"
        embed.description += f"Market Cap      : ${int(nano['mcap']):,}\n"
        embed.description += "```"
    if btc is not None:
        embed.set_footer(text='1 BTC = ${0:,.2f} | 1 NANO = {1:,.2f} BAN | Market Data Provided by CoinGecko.com'.format(btc['usdprice'], banpernan))
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
    if message.author.id not in SUPERS:
        if SPAM_THRESHOLD > tdelta.seconds:
            await post_response(message, "No more memes for {0} seconds", (SPAM_THRESHOLD - tdelta.seconds))
            return
    last_meme[message.channel.id] = datetime.datetime.now()
    meme = db.get_next_meme()
    if meme is None:
        await post_response(message, "There are no memes! Add some with !addmeme")
        return
    embed = discord.Embed(colour=discord.Colour.green())
    embed.title = "Meme #{0} - {1}".format(meme['id'], meme['title'])
    embed.set_author(name=meme['author'])
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
    if message.author.id not in SUPERS:
        if SPAM_THRESHOLD > tdelta.seconds:
            await post_response(message, "No more meows for {0} seconds", (SPAM_THRESHOLD - tdelta.seconds))
            return
    last_meow[message.channel.id] = datetime.datetime.now()
    meow = db.get_next_meow()
    if meow is None:
        await post_response(message, "There are no meows! Add some with !addmeow")
        return
    embed = discord.Embed(colour=discord.Colour.orange())
    embed.title = "Meow #{0} - {1}".format(meow['id'], meow['title'])
    embed.set_author(name=meow['author'])
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
async def fridge(ctx):
    message = ctx.message
    if is_private(message.channel):
        return
    elif message.channel.id in settings.no_spam_channels:
        return
	# Check spam
    global last_fridge
    if message.channel.id not in last_fridge:
        last_fridge[message.channel.id] = datetime.datetime.now()
    tdelta = datetime.datetime.now() - last_fridge[message.channel.id]
    if message.author.id not in SUPERS:
        if SPAM_THRESHOLD > tdelta.seconds:
            await post_response(message, "No more fridges for {0} seconds", (SPAM_THRESHOLD - tdelta.seconds))
            return
    last_fridge[message.channel.id] = datetime.datetime.now()
    fridge = db.get_next_fridge()
    if fridge is None:
        await post_response(message, "There are no fridges! Add some with !addfridge")
        return
    embed = discord.Embed(colour=discord.Colour.orange())
    embed.title = "fridge #{0} - {1}".format(fridge['id'], fridge['title'])
    embed.set_author(name=fridge['author'])
    embed.set_image(url=fridge['url'])
    await message.channel.send(embed=embed)

@client.command(aliases=["fridges"])
async def fridgelist(ctx):
    message = ctx.message
    fridges = db.get_fridges()
    if len(fridges) == 0:
        embed = discord.Embed(colour=discord.Colour.red())
        embed.title="No fridges"
        embed.description="There no fridges. Add fridges with `{0}addfridge`".format(COMMAND_PREFIX)
        await message.author.send(embed=embed)
        return
    title="fridge List"
    description=("Here are all the fridges!")
    entries = []
    for fridge in fridges:
        entries.append(paginator.Entry(str(fridge['id']),fridge['url']))

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
    if message.author.id not in SUPERS:
        if SPAM_THRESHOLD > tdelta.seconds:
            await post_response(message, "No more pups for {0} seconds", (SPAM_THRESHOLD - tdelta.seconds))
            return
    last_pup[message.channel.id] = datetime.datetime.now()
    pup = db.get_next_pup()
    if pup is None:
        await post_response(message, "There are no pups! Add some with !addpup")
        return
    embed = discord.Embed(colour=discord.Colour.blue())
    embed.title = "Pup #{0} - {1}".format(pup['id'], pup['title'])
    embed.set_author(name=pup['author'])
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

@client.command()
async def fodl(ctx, *, username):
    message = ctx.message
    #hard-coding mining channel in here for now. no one else should need this command...
    #could allow this in private message, but don't want to pollute the global with everyones chat id's
    if message.channel.id not in [566268199210057728, 443787679457345536]:  # and not is_private(message.channel):
        return

    global last_fodl
    if message.channel.id not in last_fodl:
        last_fodl[message.channel.id] = datetime.datetime.now()
    tdelta = datetime.datetime.now() - last_fodl[message.channel.id]
    if message.author.id not in SUPERS:
        if 5 > tdelta.seconds: #i think the global spam limits would be too high.
            await message.author.send("No more fodl for {0} seconds".format(5 - tdelta.seconds))
            return
    last_fodl[message.channel.id] = datetime.datetime.now()

    #a pretty safe name check. could be better
    if len(username) > 20 or len(username) < 5 or username.isalnum()==False:
        await message.author.send("Definitely not a bananominer username.")
        await message.add_reaction('\U00002753')
        return
    await message.add_reaction('\U0001F4C1') #add folder emoji to message
    output = ""
    isCorrect = True
    username = username.lower()
    getDataBase = await api.getFODLJSON(username)
    fahAPIJSON = getDataBase[0]
    bMinerJSON = getDataBase[1]
    fahBonusJSON = getDataBase[2]
    banUnits = 0
    if(bMinerJSON == {} or fahAPIJSON=={} ):
        await ctx.send("API Error")
        return

    #Verify username is valid bananominer username, im not 100% about all the errors that are possible, but thought it was safe to print the error.
    if "error" in bMinerJSON:
        output+="<:x:835354642308661278> " +username+" not a valid Bananominer username.\nUpdate username by putting banano wallet address into <https://bananominer.com/> and copy/pasting into folding at home client \n"
        isCorrect = False
        await message.add_reaction('\U0001F58D')
    else: #if no error, don't see why wouldn't be valid username...
        output+="<:white_check_mark:835347973503451176> "+username+ " is a valid bananominer username\n"

    banTeam = {}
    nonBanWU = 0
    #Verify folding for correct team and last time folded for correct team
    if "name" not in fahAPIJSON or "teams" not in fahAPIJSON:
        output+="<:x:835354642308661278> User \"" + username + "\" has not completed a Work Unit\n"
        isCorrect = False
        await message.add_reaction('\U000026D4')

    elif "teams" in fahAPIJSON:
        for team in fahAPIJSON["teams"]:
            if team["team"] == 234980 and "wus" in team:
                banTeam = team
            elif "wus" in team:
                nonBanWU += team["wus"]
        if  banTeam == {}:
            output+="<:x:835354642308661278> User: \""+ username + "\" has not folded for banano team ID 234980\n"
            isCorrect = False
            await message.add_reaction('\U000026D4')

    if (isCorrect):
        clickerStr = "<:arrow_right:856238567713800222> Click here for: "
        if "last" in banTeam: #might need to investigate further but sometimes fah api doesn't have data...
            output+="<:white_check_mark:835347973503451176> " + str(banTeam["last"])+" UTC : Last Completed Banano WU\n"
        output+="<:white_check_mark:835347973503451176> "+str(banTeam["wus"])+" work units completed so far.\n"
        output+="<:white_check_mark:835347973503451176> "+str(banTeam["score"])+" points received so far.\n"
        await message.add_reaction('\U0001F6F0')
        if   len(bMinerJSON["payments"]) == 0:
            output+="<:grey_exclamation:835357988432642049> No payments sent yet. First payment is within 24-36 hours of completing first Work Unit as long as you complete at least 2 work units (progress bar going to 100%) with at least one in each 12 hour period.\n"
            output+="<:banana:838483242113957898>Work Units Pending Payment: "+str(banTeam["wus"])+"\n"
            output+="<:banana:838483242113957898>Points Pending Payment: "+str(banTeam["score"])+"\n"
            await message.add_reaction('\U0001F6F0')
        elif len(bMinerJSON["payments"]) > 0: #user has received payments
            output+="<:white_check_mark:835347973503451176> " + bMinerJSON["payments"][0]["created_at"] + " UTC was latest payment for user.\n"
            output+="<:banana:838483242113957898>Work Units Pending Payment: "+str(banTeam["wus"]-bMinerJSON["payments"][0]["work_units"])+"\n"
            output+="<:banana:838483242113957898>Points Pending Payment: "+str(banTeam["score"]-bMinerJSON["payments"][0]["score"])+"\n"
            await message.add_reaction('\U0001F34C')
        await message.add_reaction('\U00002705')
        bonus = False
        progresso = False
        for cpu in fahBonusJSON:
            progresso = True
            if cpu["active"]==1:
                bonus = True
                output += "<:white_check_mark:835347973503451176> Passkey Bonus Active\n"
                await message.add_reaction('\U0001F510')#lock/key
                break
        if bonus ==False and progresso == True: #passkey in porgress
            output += "<:grey_exclamation:835357988432642049>  Passkey Bonus     Not Active, but appears to be in progress\n"+clickerStr+ "[Passkey Bonus Info](https://foldingathome.org/support/faq/points/?lng=en-US#what-are-the-qualifications-for-the-qrb)\nPasskey Requires 10 work units completed after adding to client to activate."
            await message.add_reaction('\U0001F6B8')#caution sign?
        elif bonus ==False:  #if there is no bonus entries, passkey is not entered (the issue here is a timeout could happen and not be deteceted...)
            output += "<:grey_exclamation:835357988432642049>  Passkey Bonus     Not Active and does not appear to be entered \n <:arrow_right:856238567713800222> Click here to: [Get a Passkey](https://apps.foldingathome.org/getpasskey)\n"+clickerStr+ "[Passkey Bonus Info](https://foldingathome.org/support/faq/points/?lng=en-US#what-are-the-qualifications-for-the-qrb)\nPasskey Requires 10 work units completed after adding to client to activate."
            await message.add_reaction('\U00002755')#exclamation mark
            #add reaction to message
    #This is not explicitly an issue, but calling it out in summary may hep in identifying wrong team issues, calling out the date(s) might also be helpful?
    if nonBanWU > 0:
        output+="<:grey_exclamation:835357988432642049> "+username + " has completed "+ str(nonBanWU) + " number of Work Units for teams other than Banano\n"
    if (isCorrect==False):
        output+="\nPlease review above errors. After updating client and completing another Work Unit: this test can be ran again to verify your client is set up to track points correctly.\n"

    output = output+"\n"
    if "id" in fahAPIJSON: output+=clickerStr+ "[F@H Donor Stat Page](https://stats.foldingathome.org/donor/"+str(fahAPIJSON["id"])+") \n"
    output+=clickerStr+"[Bananominer JSON Stats](https://bananominer.com/user_name/"+username+")\n"
    output+="FODL Check might be cached and may not update immediately.\n"
    embed = discord.Embed(colour=discord.Colour.teal())
    embed.title = "FODL Check"
    embed.description = output
    await message.author.send( embed=embed)


@client.command(aliases=["wban"])
async def farms(ctx):
    message = ctx.message
    global last_farms
    if message.channel.id not in last_farms:
        last_farms[message.channel.id] = datetime.datetime.now() - datetime.timedelta(seconds=SPAM_THRESHOLD) 

    tdelta = datetime.datetime.now() - last_farms[message.channel.id]
    if message.author.id not in SUPERS:
        if SPAM_THRESHOLD > tdelta.seconds:
            await message.author.send("No more farms for {0} seconds".format(SPAM_THRESHOLD - tdelta.seconds))
            return

    last_farms[message.channel.id] = datetime.datetime.now()
    #Get the API response
    apiResponse = await api.getWbanFarms()
    #In case something went wrong
    if apiResponse is None:
        await ctx.send("API Error")
        return
    if apiResponse == []:
        await ctx.send("No active wBAN farms found")
        return
        
    #Sort the response so that the networks are always in the same order
    apiResponse.sort(key=lambda y: y[0])

    output = ""
    #Maps networks to their corresponding wban emoji. This part will need to be updated for future networks (will map to bsc emoji by default)
    emoji_map = {
        "binance-smart-chain":"<:wbanbsc:835977496389877802>", 
        "fantom":"<:wbanftm:949720720110419999>", 
        "polygon":"<:wbanpoly:884560016928043038>",
        "ethereum":"<:wbaneth:1037739681401536662>",
        "arbitrum":"<:wbanarb:1051565681763688548>"
    } 
    for (network,farms) in apiResponse:
        #Get the emoji for this network 
        if network in emoji_map:
            emoji = emoji_map[network]
        else:
            emoji = emoji_map["binance-smart-chain"]
        #Build the output 
        output += f"\n{emoji} **{str.title(network)}**"
        output += "\n```"
        for (pair,tvl,apr) in farms:
            if apr is not None:
                output += f"{pair}: {apr}% APR (${tvl:,} TVL)\n"
            else:
                output += f"{pair}: Inactive (${tvl:,} TVL)\n"
        if len(farms) == 0:
            output += f"No pools found\n"
        output += "```"
    embed = discord.Embed(colour=discord.Colour.green())
    embed.title = "wBAN Farms"
    embed.description = output
    await message.channel.send(embed=embed)


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

@client.command()
async def addfridge(ctx, url: str = None, author: str = None, title: str = None):
    message = ctx.message
    if not is_admin(message.author):
        return
    elif url is None or author is None or title is None:
        await post_usage(message, ADDFRIDGE)
    elif not valid_url(url):
        await message.author.send("Invalid URL. Valid urls begin with http:// or https://")
    elif db.add_fridge(url, author, title):
        await message.author.send("fridge added: {0}".format(title))
    else:
        await message.author.send("Could not add fridge {0}. It may already exist".format(url))

@client.command()
async def removefridge(ctx, id: str):
    message = ctx.message
    if not is_admin(message.author):
        return
    elif db.remove_fridge(id):
        await message.author.send("fridge {0} removed".format(id))
    else:
        await message.author.send("Could not remove fridge {0}. It may not exist".format(id))

@client.command(aliases=['muzzle'])
async def mute(ctx):
	message = ctx.message
	if is_admin(message.author):
		targets = get_all_mentions(message)
		if len(targets) > 0:
			muzzled = message.guild.get_role(settings.muzzled_role)
			duration = find_amount(message.content)
			expiration = None
			if duration is not None:
				try:
					expiration = datetime.datetime.now() + datetime.timedelta(minutes=float(duration))
				except:
					expiration = None
			for member in targets:
				if not db.silence(member.id, message.guild.id, expiration=expiration):
					await post_response(message, '<@{0}> is already muzzled', member.id)
					continue
				await member.add_roles(muzzled)
				if duration is not None:
					await post_response(message, '<@{0}> has been muzzled for {1} minutes', member.id, duration)
				else:
					await post_response(message, '<@{0}> has been muzzled indefinitely', member.id)
			await message.add_reaction('\U0001f694')

@client.command(aliases=['unmuzzle'])
async def unmute(ctx):
	message = ctx.message
	if is_admin(message.author):
		targets = get_all_mentions(message)
		if len(targets) > 0:
			muzzled = message.guild.get_role(settings.muzzled_role)
			for member in targets:
				await member.remove_roles(muzzled)
				if not db.unsilence(member.id):
					await post_response(message, '<@{0}> is not muzzled', member.id)
					continue
				await post_response(message, '<@{0}> has been unmuzzled', member.id)
@client.command()
async def arrest(ctx):
	message = ctx.message
	if is_admin(message.author):
		targets = get_all_mentions(message)
		if len(targets) > 0:
			jail = message.guild.get_role(settings.ARREST_ROLE)
			for member in targets:
				await member.add_roles(jail)
				await post_response(message, settings.RIGHTS, mention_id=member.id, channel_id=settings.JAIL_ID)
			await message.add_reaction('\U0001f694')

@client.command()
async def release(ctx):
	message = ctx.message
	if is_admin(message.author):
		targets = get_all_mentions(message)
		if len(targets) > 0:
			# Tip unban too
			jail = message.guild.get_role(settings.ARREST_ROLE)
			for member in targets:
				await member.remove_roles(jail)
				await post_response(message, settings.RELEASE, mention_id=member.id)

@client.command()
async def troll(ctx):
	message = ctx.message
	if is_admin(message.author):
		targets = get_all_mentions(message)
		if len(targets) > 0:
			troll = message.guild.get_role(settings.TROLL_ROLE)
			citizenship = message.guild.get_role(settings.CITIZEN_ROLE)
			for member in targets:
				await member.add_roles(troll)
				await member.remove_roles(citizenship)
				await post_response(message, settings.TROLL, mention_id=member.id)

@client.command()
async def untroll(ctx):
	message = ctx.message
	if is_admin(message.author):
		targets = get_all_mentions(message)
		if len(targets) > 0:
			troll = message.guild.get_role(settings.TROLL_ROLE)
			for member in targets:
				await member.remove_roles(troll)
				await post_response(message, settings.UNTROLL, mention_id=member.id)

@client.command()
async def citizenship(ctx):
	message = ctx.message
	if is_admin(message.author):
		targets = get_all_mentions(message)
		if len(targets) > 0:
			citizenship = message.guild.get_role(settings.CITIZEN_ROLE)
			for member in targets:
				await member.add_roles(citizenship)
				await post_response(message, settings.CITIZENSHIP, mention_id=member.id)
			await message.add_reaction('\:bananorepublic:429691019538202624')

@client.command()
async def deport(ctx):
	message = ctx.message
	if is_admin(message.author):
		targets = get_all_mentions(message)
		if len(targets) > 0:
			citizenship = message.guild.get_role(settings.CITIZEN_ROLE)
			for member in targets:
				await member.remove_roles(citizenship)
				await post_response(message, settings.DEPORT, mention_id=member.id)
			await message.add_reaction('\U0001F6F3')

@client.command()
async def noimages(ctx):
	message = ctx.message
	if is_admin(message.author):
		targets = get_all_mentions(message)
		if len(targets) > 0:
			imagesperm = message.guild.get_role(settings.IMAGES_ROLE)
			for member in targets:
				await member.add_roles(imagesperm)
			await message.add_reaction('\U0001F485')

@client.command()
async def allowimages(ctx):
	message = ctx.message
	if is_admin(message.author):
		targets = get_all_mentions(message)
		if len(targets) > 0:
			imagesperm = message.guild.get_role(settings.IMAGES_ROLE)
			for member in targets:
				await member.remove_roles(imagesperm)
			await message.add_reaction('\U0001F3A8')

@client.command()
async def kick(ctx):
    message = ctx.message
    if not is_admin(message.author):
        return
    logchannel = message.guild.get_channel(settings.KICK_LOG)
    # Check if they are beyond threshold
    redis = await util.get_redis()
    kick_count = await redis.get(f"kickcount_{message.author.id}")
    if kick_count is not None:
        if int(kick_count) > 15:
            await logchannel.send(f"<@{message.author.id}> is kicking people excessively! <@303599885800964097>")
    # Extract reason from text
    reason=None
    if 'reason=' in message.content:
        idx = message.content.index('reason=')
        if message.content[idx+7] == '"' or message.content[idx+7] == "'" or message.content[idx+7] == '”':
            firstidx = idx+8
            lastidx = max([message.content.rindex('"') if '"' in message.content else -1, message.content.rindex('\'') if '\'' in message.content else -1, message.content.rindex('”') if '”' in message.content else -1])
        else:
            firstidx = idx+7
            lastidx = len(message.content)
        reason = message.content[firstidx:lastidx]
    # Get kick list
    message.content = ' '.join(message.content.split('\n'))
    targets = get_all_mentions(message)
    kicked_users = []
    for member in targets:
        if is_admin(member):
            continue
        kicked_users.append(member)
        await message.guild.kick(member, reason=reason)
    if len(kicked_users) == 0:
        await message.author.send(f"No users to kick, {len(targets)} users are inelligble")
        return
    # Log incident
    if len(kicked_users) > 15:
        await logchannel.send(f"<@{message.author.id}> is kicking people excessively! <@303599885800964097>")
    kick_count = await redis.get(f"kickcount_{message.author.id}")
    total_kicked = len(kicked_users)
    if kick_count is not None:
        total_kicked += int(kick_count)
    # Keep kick count in redis for 10 minutes
    await redis.set(f"kickcount_{message.author.id}", str(total_kicked), expire=600)
    # Log in channel
    user_list_str = ""
    for x in kicked_users:
        user_list_str += f"{x.mention} "
    await logchannel.send(f"<@{message.author.id}> KICKED {len(kicked_users)} users: {user_list_str} reason: {'Not Specified' if not reason else reason}")

@client.command()
async def ban(ctx):
    message = ctx.message
    if not is_admin(message.author):
        return
    logchannel = message.guild.get_channel(settings.KICK_LOG)
    # Check if they are beyond threshold
    redis = await util.get_redis()
    ban_count = await redis.get(f"bancount_{message.author.id}")
    if ban_count is not None:
        if int(ban_count) > 10:
            await logchannel.send(f"<@{message.author.id}> is banning people excessively! <@303599885800964097>")
    # Extract reason from text
    reason=None
    if 'reason=' in message.content:
        idx = message.content.index('reason=')
        if message.content[idx+7] == '"' or message.content[idx+7] == "'" or message.content[idx+7] == '”':
            firstidx = idx+8
            lastidx = max([message.content.rindex('"') if '"' in message.content else -1, message.content.rindex('\'') if '\'' in message.content else -1, message.content.rindex('”') if '”' in message.content else -1])
        else:
            firstidx = idx+7
            lastidx = len(message.content)
        reason = message.content[firstidx:lastidx]
    # Get ban list
    message.content = ' '.join(message.content.split('\n'))
    targets = get_all_mentions(message)
    banned_users = []
    for member in targets:
        if is_admin(member):
            continue
        banned_users.append(member)
        await message.guild.ban(member, reason=reason, delete_message_days=0)
    if len(banned_users) == 0:
        await message.author.send(f"No users to ban, {len(targets)} users are inelligble")
        return
    # Log incident
    if len(banned_users) > 10:
        await logchannel.send(f"<@{message.author.id}> is banning people excessively! <@303599885800964097>")
    ban_count = await redis.get(f"bancount_{message.author.id}")
    total_banned = len(banned_users)
    if ban_count is not None:
        total_banned += int(ban_count)
    # Keep ban count in redis for 5 minutes
    await redis.set(f"bancount_{message.author.id}", str(total_banned), expire=300)
    # Log in channel
    user_list_str = ""
    for x in banned_users:
        user_list_str += f"{x.mention} "
    await logchannel.send(f"<@{message.author.id}> BANNED {len(banned_users)} users: {user_list_str} reason: {'Not Specified' if not reason else reason}")

@client.command()
async def ids(ctx):
    message = ctx.message
    resp = ""
    for men in message.mentions:
        resp += f"{men.id} "
    await message.author.send(f"{resp.strip()}")

### Re-Used Discord Functions
async def post_response(message, template, *args, mention_id=None, channel_id=None):
    if mention_id is None:
        mention_id = message.author.id
    if channel_id is None:
        channel = message.channel
    else:
        try:
            channel = message.guild.get_channel(channel_id)
        except AttributeError:
            channel = message.channel
            logger.warn("Could not find jail channel on server. Check that the configured jail channel is correct.")
    response = template.format(*args)
    if not is_private(message.channel):
        response = "<@" + str(mention_id) + "> \n" + response
    logger.info("sending response: '%s' for message: '%s' to userid: '%s' name: '%s'", response, message.content, message.author.id, message.author.name)
    await asyncio.sleep(0.05) # Slight delay to avoid discord bot responding above commands
    return await channel.send(response)

async def post_usage(message, command):
    embed = discord.Embed(colour=discord.Colour.purple())
    embed.title = "Usage:"
    embed.add_field(name=command['CMD'], value=command['USAGE'],inline=False)
    await message.author.send(embed=embed)

#

def find_amount(input_text):
	regex = r'(?:^|\s)(\d*\.?\d+)(?=$|\s)'
	matches = re.findall(regex, input_text, re.IGNORECASE)
	if len(matches) >= 1:
		return float(matches[0].strip())
	else:
		return None

def get_all_mentions(message):
    """Given a message, retrieves all mentioned users by both ID and discord mentions"""
    mentions = []
    if len(message.mentions) > 0:
        mentions = message.mentions
          
    if len(message.content) > 0:
        #need to consider potential edge-cases with the reason. In particular:
        # UserId in reason -> don't add to list 
        # User mentioned in message both in & outside of reason -> add to list 
        # User mentioned in message but **only** in reason -> don't add to list 
        message.content = ' '.join(message.content.split('\n'))

        #Parse out the reason
        if 'reason=' in message.content:
            idx = message.content.index('reason=')
            if message.content[idx+7] == '"' or message.content[idx+7] == "'" or message.content[idx+7] == '”':
                firstidx = idx+8
                lastidx = max([message.content.rindex('"') if '"' in message.content else -1, message.content.rindex('\'') if '\'' in message.content else -1, message.content.rindex('”') if '”' in message.content else -1])
            else:
                firstidx = idx+7
                lastidx = len(message.content)
            reason = message.content[firstidx:lastidx]
            message.content = message.content[0:idx:] + message.content[lastidx+1:]

            #Remove any users mentioned in the reason
            for split in reason.split('<@')[1:]:
                if ">" in split:
                    try:
                        user_id = int(split.split(">")[0])
                        mentions.remove(message.guild.get_member(user_id))
                    except (ValueError, IndexError):
                        pass                 

        raw_content = message.content.split(' ')
        for split in raw_content:
            try:
                user_id = int(split.strip())
                member = message.guild.get_member(user_id)
                if member != None:
                    mentions.append(member)
            except ValueError:
                pass
        #Re-add any users that are mentioned in the reason but also in the main text
        for split in message.content.split('<@')[1:]:
            if ">" in split:
                try:
                    user_id = int(split.split(">")[0])
                    member = message.guild.get_member(user_id)
                    if member != None:
                        mentions.append(member)
                except (ValueError, IndexError):
                    pass                 
    return list(set(mentions))

# Start the bot
client.run(settings.discord_bot_token)
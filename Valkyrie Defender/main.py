import discord
from discord.ext import commands

import signal
import asyncio
import aiohttp

import os
import dotenv
import datetime
import json

dotenv.load_dotenv()

bot = commands.Bot(command_prefix='*', intents=discord.Intents.all())
bot.session = aiohttp.ClientSession()
admin_channel = "valkyrie"

# Sistema de sanciones
async def print_sanction(chanel, user_id, reason, nsanc, penalization, lsanciones, server, guild):
    print("server_id:", server)
    chanel = discord.utils.get(bot.get_all_channels(), name=chanel)
    user_mention = f'<@{user_id}>'
    await chanel.send(f"[!] A penalty has been applied to you {user_mention}, you have {nsanc} penalties\nPenalization: {penalization}")
    
    chanel = discord.utils.get(bot.get_all_channels(), name=admin_channel)
    if chanel is not None:
        await chanel.send(f"[!] The user {user_mention} has been penalized (penalties: {nsanc})\nReason: {reason}\nPenalization: {penalization}")
        if nsanc >= 5:
            admin_role = discord.utils.get(guild.roles, name="valkyrie_admin")
            admin_role_id = admin_role.id
            role_mention = f"<@&{admin_role_id}>"
            await chanel.send(f"[!] @{role_mention} The user {user_mention} has been banned because they have 5 penalties, reasons:\n```\n· {lsanciones[str(server)][str(user_id)][0]}\n· {lsanciones[str(server)][str(user_id)][1]}\n· {lsanciones[str(server)][str(user_id)][2]}\n· {lsanciones[str(server)][str(user_id)][3]}\n· {lsanciones[str(server)][str(user_id)][4]}\n```")

async def ban_user(user_id, guild, reason):
    if user_id is not None:
        member = await guild.fetch_member(user_id)
        if member is not None:
            await guild.ban(member, reason=reason)

async def timeout(user_id: int, stime: int, server):
    guild = bot.get_guild(server)
    if guild is None:
        return "Could not find guild"
    member = guild.get_member(str(user_id))
    if member is None:
        return "Could not find member"
    handshake = await timeout_user(user_id=user_id, guild_id=guild.id, until=stime)
    if handshake:
        return f"Successfully timed out user {member.display_name} for {stime} minutes."
    return "Something went wrong"

async def sancion(user_id, server, reason, chanel, member):
    guild = bot.get_guild(server)
    if guild is None:
        return "Could not find guild"
    user_id2 = str(user_id)
    server2 = str(server)
    reason = str(reason)
    chanel = str(chanel)
    
    sanciones_file_path = os.path.join(script_directory, 'sanciones.txt')

    if not os.path.exists(sanciones_file_path):
        with open(sanciones_file_path, 'w') as f:
            json.dump({}, f)

    with open(sanciones_file_path, 'r') as sanciones_file:
        lsanciones = json.load(sanciones_file)

    lsanciones.setdefault(server2, {}).setdefault(user_id2, [])
    lsanciones[server2][user_id2].append(reason)
    nsanc = len(lsanciones[server2][user_id2])

    with open(sanciones_file_path, 'w') as sanciones_file:
        json.dump(lsanciones, sanciones_file)

    penalization = ""
    if nsanc == 1:
        penalization = "An hour of timeout"
        await member.timeout(datetime.timedelta(seconds=0, minutes=0, hours=1, days=0), reason=reason)
    elif nsanc == 2:
        penalization = "A day of timeout"
        await member.timeout(datetime.timedelta(seconds=0, minutes=0, hours=0, days=1), reason=reason)
    elif nsanc == 3:
        penalization = "Two days of timeout"
        await member.timeout(datetime.timedelta(seconds=0, minutes=0, hours=0, days=2), reason=reason)
    elif nsanc == 4:
        penalization = "A week of timeout"
        await member.timeout(datetime.timedelta(seconds=0, minutes=0, hours=0, days=7), reason=reason)
    elif nsanc >= 5:
        penalization = "Ban"
        await ban_user(user_id, guild, reason)

    print(f"[!] The user {user_id2} has been penalized in {server2}, reason: {reason}")
    await print_sanction(chanel, user_id, reason, nsanc, penalization, lsanciones, server, guild)
    
    sanciones_file.close()
 
# Config
script_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(script_directory, 'config.txt'), 'w') as config:
    pass

def check_sanciones(): # para que cualquier persona mire que sanciones tiene ella u otra persona
    pass

def clear_sanciones(): # mi spanglish es una maravilla XD
    pass

with open(os.path.join(script_directory, 'blacklist.txt'), 'w') as blacklist:
    pass

# turn on
@bot.event
async def on_ready():
    print("[+] Valkyrie Defender enabled")
    chanel = discord.utils.get(bot.get_all_channels(), name=admin_channel)
    if chanel is not None:
        await chanel.send("[+] Valkyria Defender enabled")
        
async def timeout_user(*, user_id: int, guild_id: int, until):
    headers = {"Authorization": f"Bot {bot.http.token}"}
    url = f"https://discord.com/api/v9/guilds/{guild_id}/members/{user_id}"
    timeout = (datetime.datetime.utcnow() + datetime.timedelta(minutes=until)).isoformat()
    jsont = {'communication_disabled_until': timeout}
    async with bot.session.patch(url, json=jsont, headers=headers) as session:
        if session.status in range(200, 299):
            return True
        return False

# Comandos de prueba
@bot.command()
async def ping(ctx):
    await ctx.send("pong!")
    
# sancionar a un usuario
@bot.command()
@commands.has_role('valkyrie_admin')
async def penalize(ctx, user: discord.Member, reason: str):
    user_id = user.id
    server_id = ctx.guild.id
    channel = ctx.channel.name
    await sancion(user_id, server_id, reason, channel, user)
    
@bot.command()
@commands.has_role('valkyrie_admin')
async def ban(ctx, user: discord.Member, reason: str):
    await user.ban(reason=reason)
    chanel = discord.utils.get(bot.get_all_channels(), name=admin_channel)
    if chanel is not None:
        await chanel.send(f"[!] The user {user} has been penalized!\nReason: {reason}\nPenalization: ban")
        await chanel.send(f"[!] @valkyrie_admin The user {user} has been banned!")

# help
@bot.command()
async def Help(ctx):
    await ctx.send(str("When finished the bot, probably i'm going to upload a guide to: https://airilmusic.github.io"+
                   "\n\nCOMMAND LIST:"+
                   "\n```\n*pin: to check if the bot is working "+
                   "\n*check_sanctions @user: see how many penalties a user has"+
                   "\n\nSANCTIONS:"+
                   "\n    1 --> An hour of timeout"+
                   "\n    2 --> A day of timeout"+
                   "\n    3 --> Two days of timeout"+
                   "\n    4 --> A week of timeout"+
                   "\n    5 --> BAN, and this user will be added to a multiserver blacklist\n"+
                   "\nADMIN COMMANDS:"+
                   "\n*ban @user reason: to ban a user (only users with the rol 'valkirye_admin' can execute this command)"+ 
                   "\n*penalize @user reason: to give one penalization to a user (only users with the rol 'valkirye_admin' can execute this command)"+
                   "\n```"))

# Easter eggs
# BUSCADLOS JEJE

# Shut Down
def signal_handler(sig, frame):
    asyncio.get_event_loop().call_soon_threadsafe(asyncio.create_task, handle_signal(sig))

async def handle_signal(sig):
    print("[!] Valkyrie Defender disabled")
    chanel = discord.utils.get(bot.get_all_channels(), name=admin_channel)
    if chanel is not None:
        await chanel.send("[!] Valkyria Defender disabled")
    print("[!] Bot has been stopped.")
    await bot.close()

signal.signal(signal.SIGINT, signal_handler)

bot.run(os.getenv('DISCORD_TOKEN')) # API KEY

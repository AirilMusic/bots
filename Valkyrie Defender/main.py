import discord
from discord.ext import commands

import signal
import asyncio
import aiohttp

import os
import datetime
import json

bot = commands.Bot(command_prefix='*', intents=discord.Intents.all())
bot.session = aiohttp.ClientSession()
admin_channel = "valkyrie"

# Sistema de sanciones
async def print_sanction(chanel, user_id, reason, nsanc, penalization, lsanciones, server):
            chanel = discord.utils.get(bot.get_all_channels(), name=chanel)
            user_mention = f'<@{user_id}>'
            await chanel.send(f"[!] A penalty has been applied to you {user_mention}, you have {nsanc} penalties\nPenalization: {penalization}")
            
            chanel = discord.utils.get(bot.get_all_channels(), name=admin_channel)
            if chanel is not None:
                await chanel.send(f"[!] The user {user_mention} has been penalized (penalties: {nsanc})\nReason: {reason}\nPenalization: {penalization}")
                if nsanc >= 5:
                    await chanel.send(f"[!] @valkyrie_admin The user {user_mention} has been banned because they have 5 penalties, reasons:\n```\n·{lsanciones[server][user_id][0]}\n·{lsanciones[server][user_id][1]}\n·{lsanciones[server][user_id][2]}\n·{lsanciones[server][user_id][3]}\n·{lsanciones[server][user_id][4]}")

async def ban_user(user_id, guild_id, reason, chanel, nsanc, penalization, lsanciones):
    guild = bot.get_guild(guild_id)
    user = await guild.fetch_member(user_id)
    if user is not None:
        await guild.ban(user, reason=reason)
        await print_sanction(chanel, user_id, reason, nsanc, penalization, lsanciones, guild)

async def timeout(user_id: int, stime: int, server):
            guild = bot.get_guild(server)
            member = guild.get_member(user_id)
            if member is None:
                return "Could not find member"
            handshake = await timeout_user(user_id=user_id, guild_id=guild.user_id, until=stime)
            if handshake:
                return f"Successfully timed out user {member.display_name} for {stime} minutes."
            return "Something went wrong"

async def sancion(user_id, server, reason, chanel):
    with open(os.path.join(script_directory, 'sanciones.txt'), 'r+') as sanciones_file:
        lsanciones = json.load(sanciones_file)
        
        if server not in lsanciones:
            lsanciones[server] = {}
        if user_id not in lsanciones[server]:
            lsanciones[server][user_id] = []
        
        lsanciones[server][user_id].append(reason)
        nsanc = len(lsanciones[server][user_id])
        
        penalization = ""
        if nsanc == 1:
            penalization = "An hour of timeout"
            timeout(user_id, 60, server)
        elif nsanc == 2:
            penalization = "A day of timeout"
            timeout(user_id, 1440, server)
        elif nsanc == 3:
            penalization = "Two days of timeout"
            timeout(user_id, 2880, server)
        elif nsanc == 4:
            penalization = "A week of timeout"
            timeout(user_id, 10080, server)
        elif nsanc >= 5:
            penalization = "Ban"
        
        print(f"[!] The user {user_id} has been penalized in {server}, reason: {reason}")
        print_sanction(chanel, user_id, reason, nsanc, penalization, lsanciones, server)
        
        if nsanc >= 5:
            ban_user(user_id, server, reason, chanel, nsanc, penalization, lsanciones)
        
        sanciones_file.seek(0)
        sanciones_file.truncate()
        json.dump(lsanciones, sanciones_file)

# Config
script_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(script_directory, 'config.txt'), 'w') as config:
    pass


def check_sanciones(): # para que cualquier persona mire que sanciones tiene ella u otra persona
    pass

def clear_sanciones(): # mi spanglish es una maravilla XD
    pass

with open(os.path.join(script_directory, 'blacklist.txt'), 'w') as blacklist:
    #blacklist.write('Hola mundo!\n')
    #blacklist.read()
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
async def ban(ctx, user: discord.Member, reason: str):
    await user.ban(reason=reason)
    chanel = discord.utils.get(bot.get_all_channels(), name=admin_channel)
    if chanel is not None:
        await chanel.send(f"[!] The user {user} has been penalized!\nReason: {reason}\nPenalization: {reason}")
        await chanel.send(f"[!] @valkyrie_admin The user {user} has been banned!")

# Easter eggs
"LOS BUSCAIS"

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

bot.run('API KEY') # API KEY
import discord # pip install discord
from discord.ext import commands

import signal
import asyncio # pip install asyncio
import aiohttp # pip install aiohttp

import os
import re
import dotenv # pip install python-dotenv
import datetime
import json
import nacl # pip install pynacl
import requests

dotenv.load_dotenv() # antes que nada, mi spanglish es una maravilla, ya lo se XD

bot = commands.Bot(command_prefix='*', intents=discord.Intents.all())
bot.session = aiohttp.ClientSession()
admin_channel = "valkyrie"
log_channel = "valkyrie-logs"

# Configuración de Sightengine, para la deteccion de imagenes nsfw
API_USER = os.getenv("SIGHTENGINE_USER")
API_SECRET = os.getenv("SIGHTENGINE_SECRET")
sightengine_url = "https://api.sightengine.com/1.0/check.json"
virus_total_key = os.getenv("VIRUS_TOTAL")

script_directory = os.path.abspath(os.path.dirname(__file__))
config = {}

# config file
def load_config():
    config_file_path = os.path.join(script_directory, 'config.txt')
    if not os.path.exists(config_file_path):
        with open(config_file_path, 'w') as f:
            json.dump({}, f)
    with open(config_file_path, 'r') as config_file:
        return json.load(config_file)

def save_config(config):
    config_file_path = os.path.join(script_directory, 'config.txt')
    with open(config_file_path, 'w') as config_file:
        json.dump(config, config_file)

config = load_config()

# recordatorios
def load_remember():
    remember_file_path = os.path.join(script_directory, 'remember.txt')
    if not os.path.exists(remember_file_path):
        with open(remember_file_path, 'w') as f:
            json.dump({}, f)
    with open(remember_file_path, 'r') as remember_file:
        return json.load(remember_file)

def save_remember(config):
    remember_file_path = os.path.join(script_directory, 'remember.txt')
    with open(remember_file_path, 'w') as remember_file:
        json.dump(config, remember_file)

remember = load_remember()

# config badwords
@bot.command()
async def show_badwords(ctx):
    config = load_config()
    server_id = str(ctx.guild.id)
    if server_id in config and config[server_id]["badwords"]:
        badwords = '\n'.join(config[server_id]["badwords"])
        embed = discord.Embed(title=f"Server '{ctx.guild.name}' badwords:", description=badwords, color=discord.Color.blue())
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"There are no badwords in '{ctx.guild.name}' server.")

@bot.command()
@commands.has_role('valkyrie_admin')
async def add_badword(ctx, word: str):
    config = load_config()
    server_id = str(ctx.guild.id)
    if server_id not in config:
        config[server_id] = {"badwords":[], "ban_blacklisted_users":False, "user_verification":False}
    config[server_id]["badwords"].append(word.lower())
    save_config(config)
    await ctx.send(f"The badword: '{word}' has been added to the server '{ctx.guild.name}' badwords list.")

@bot.command()
@commands.has_role('valkyrie_admin')
async def remove_badword(ctx, word: str):
    config = load_config()
    server_id = str(ctx.guild.id)
    if server_id in config and word.lower() in config[server_id]["badwords"]:
        config[server_id]["badwords"].remove(word.lower())
        save_config(config)
        await ctx.send(f"'{word}' badword has been removed from '{ctx.guild.name}' server.")
    else:
        await ctx.send(f"'{word}' is not a badword in '{ctx.guild.name}' server.")

# detectar informacion sensible y badwords, and spam locker
sensitive_words = ["password", "Password", "pass", "Pass", "username", "Username", "contraseña", "Contraseña", "Nombre de usuario", "nombre de usuario", "Tarjeta de credito", "tarjeta de credito", "Credit card", "credit card", "Dirección", "dirección", "Direccion", "direccion", "Address", "address", "Fecha de nacimiento", "fecha de nacimiento", "Date of birth", "date of birth", "Teléfono", "Telefono", "telefono", "teléfono", "Phone number", "phone number", "Correo electronico", "Correo electrónico", "correo electrónico", "correo electronico", "gmail", "Gmail", "Email", "email", "Pasaporte", "pasaporte", "Passport", "passport", "Número de cuenta", "Numero de cuenta", "número de cuenta", "numero de cuenta", "Account number", "account number", "Nombre completo", "nombre completo", "Full name", "full name", "Dirección de facturación", "Direccion de facturacion", "dirección de facturación", "direccion de facturacion", "Billing address", "billing address", "DNI:", "dni:"]

message_counts = {}

# Function to check if an image is NSFW
def is_nsfw(image_url):
    params = {
      'models': 'nudity-2.0',
      'api_user': API_USER,
      'api_secret': API_SECRET
    }
    files = {'media': requests.get(image_url).content}
    r = requests.post('https://api.sightengine.com/1.0/check.json', files=files, data=params)

    output = json.loads(r.text)
    print(output)
    return output['nudity']['none'] < 0.5

@bot.event
async def on_message(message):
    config = load_config()
    if message.author.bot:
        return

    # get badwords list for the current server
    try:
        server_id = str(message.guild.id)
        if server_id in config:
            badwords = config[server_id]['badwords']
        else:
            badwords = []
    except:
        pass

    # check if any badword is present in the message
    try:
        for word in badwords:
            if word in message.content.lower():
                author_roles = [r.name for r in message.author.roles]
                if 'valkyrie_admin' in author_roles:
                    break
                await message.delete()
                channel = discord.utils.get(message.guild.channels, name=admin_channel)
                await channel.send(f"The message from {message.author.mention} has been deleted for containing a forbidden word in this server: {word}")
                await warn_user(channel, message.author.id, message.guild.id, f"Message contained forbidden word: {word}", message.guild.name, message.author.name, channel.name)
                return
    except:
        pass
    
    # sensitive words check
    if message.guild:
        for word in sensitive_words:
            if word in message.content.lower():
                channel = discord.utils.get(message.guild.channels, name=admin_channel)
                
                try:
                    admin_role = discord.utils.get(message.guild.roles, name="valkyrie_admin")
                    role_mention = admin_role.mention
                    await channel.send(f"{role_mention}")
                except:
                    pass
                
                embed_message = discord.Embed(
                    title=f"Message with possible sensitive information or phishing attempt by {message.author.display_name} (react to delete it):",
                    description=message.content,
                    color=0xFF0000,
                    timestamp=datetime.datetime.utcnow()
                )
                
                embed_message.set_footer(text="Message send at")

                bot_message = await channel.send(embed=embed_message)
                await bot_message.add_reaction("👍")
                await bot_message.add_reaction("👎")

                def check(reaction, user):
                    return str(reaction.emoji) in ['👍', '👎'] and reaction.message.id == bot_message.id

                try:
                    reaction, user = await bot.wait_for('reaction_add', check=check)
                except asyncio.TimeoutError:
                    await bot_message.delete()
                else:
                    if str(reaction.emoji) == "👍":
                        await message.delete()
                return
    
    # lock spam
    try:
        user_id = message.author.id
        content = message.content.lower()
        server_id = message.guild.id
        channel = message.channel
        

        if server_id not in message_counts:
            message_counts[server_id] = {}

        if user_id not in message_counts[server_id]:
            message_counts[server_id][user_id] = {
                "last_message": None,
                "count": 0
            }

        if content == message_counts[server_id][user_id]["last_message"]:
            message_counts[server_id][user_id]["count"] += 1
        else:
            message_counts[server_id][user_id]["count"] = 1

        message_counts[server_id][user_id]["last_message"] = content

        if message_counts[server_id][user_id]["count"] == 4:
            await warn_user(channel, message.author.id, message.guild.id, "spam", message.guild.name, message.author.name, channel.name)

        if message_counts[server_id][user_id]["count"] == 5:
            await sancion(user_id, message.guild.id, "spam", channel.name, message.author)
    except:
        pass
    
    # Comprobar si el mensaje tiene una imagen nsfw
    if len(message.attachments) > 0:
        try:
            image_url = message.attachments[0].url
            if is_nsfw(image_url):
                # Check if the channel is not NSFW y si el user tiene role 'valkyrie_admin'
                if not message.channel.is_nsfw():
                    if 'valkyrie_admin' not in [role.name for role in message.author.roles]:
                        await message.delete()
                        await message.channel.send("You cannot send NSFW photos through a channel that is not meant for it!")
        except:
            pass # el archivo no es una foto
        
    # Verificar si el mensaje contiene una URL maliciosa o no
    isGif = False
    
    urls = re.findall("(?P<url>https?://[^\s]+)", message.content)
    for url in urls:
        if "tenor.com" in url:
            isGif = True
            break
    
    if "http" in message.content and isGif == False:
        url = message.content.split(" ")[0]
        params = {"apikey": virus_total_key, "resource": url}
        response = requests.get("https://www.virustotal.com/vtapi/v2/url/report", params=params)

        if response.json()['response_code'] > 0:
            admin_role = discord.utils.get(message.guild.roles, name="valkyrie_admin")
            admin_role_id = admin_role.id
            role_mention = f"<@&{admin_role_id}>"
            await message.channel.send(f"{role_mention}\nThe message from {message.author.mention} may contain harmful content! Please be careful when sharing and clicking on links!")
    
    # Verificar si el mensaje contiene un archivo malicioso o no
    if message.attachments:
        try:
            attachment = message.attachments[0]
            file_content = await attachment.read()

            params = {"apikey": virus_total_key}
            files = {"file": file_content}
            response = requests.post("https://www.virustotal.com/vtapi/v2/file/scan", params=params, files=files)

            resource_id = response.json()["resource"]
            params = {"apikey": os.getenv("VIRUS_TOTAL"), "resource": resource_id}
            response = requests.get("https://www.virustotal.com/vtapi/v2/file/report", params=params)
            if response.json()["positives"] > 0:  
                await message.channel.send(f"{role_mention}\nThe message from {message.author.mention} may contain harmful files! Please be careful when downloading files!")
        except:
            pass # el archivo no es valido
        
    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    if reaction.message.channel.name != admin_channel:
        return
    if str(reaction.emoji) == "👍":
        await reaction.message.channel.purge(limit=2)
    elif str(reaction.emoji) == "👎":
        await reaction.message.channel.purge(limit=2)

# blacklist
async def add_to_blacklist(user_id, reason_list):
    blacklist_file_path = os.path.join(script_directory, 'blacklist.txt')
    if not os.path.exists(blacklist_file_path):
        with open(blacklist_file_path, 'w') as f:
            json.dump({}, f)

    with open(blacklist_file_path, 'r') as blacklist_file:
        lblacklist = json.load(blacklist_file)

    for server_id, user_reasons in reason_list.items():
        for user_id, reasons in user_reasons.items():
            if user_id not in lblacklist:
                lblacklist[user_id] = reasons
    
    with open(blacklist_file_path, 'w') as blacklist_file:
        json.dump(lblacklist, blacklist_file)
    
    blacklist_file.close()

async def remove_from_blacklist(user_id):
    blacklist_file_path = os.path.join(script_directory, 'blacklist.txt')
    if not os.path.exists(blacklist_file_path):
        return

    with open(blacklist_file_path, 'r') as blacklist_file:
        lblacklist = json.load(blacklist_file)
        if user_id in lblacklist:
            del lblacklist[user_id]
    
    with open(blacklist_file_path, 'w') as blacklist_file:
        json.dump(lblacklist, blacklist_file)
    
    blacklist_file.close()

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
            channel = discord.utils.get(guild.text_channels, name=log_channel)
            embed = discord.Embed(title="Ban:", description=f"{user_mention} has baned automatically.", color=discord.Color.red())
            await channel.send(embed=embed)
            
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
        await add_to_blacklist(user_id, lsanciones)

    print(f"[!] The user {user_id2} has been penalized in {server2}, reason: {reason}")
    await print_sanction(chanel, user_id, reason, nsanc, penalization, lsanciones, server, guild)
    sanciones_file.close()

# eventos
# turn on
@bot.event
async def on_ready():
    print("[+] Valkyrie Defender enabled")
    chanel = discord.utils.get(bot.get_all_channels(), name=admin_channel)
    if chanel is not None:
        await chanel.send("[+] Valkyria Defender enabled")

# bienvenida, check blacklist y verificacion
@bot.event
async def on_member_join(member):
    config = load_config()
    server_id = str(member.guild.id)
    if server_id in config and config[server_id]['ban_blacklisted_users'] == True:
        await ban_user(member.id, member.guild, "User was blacklisted")
        return
    admin_role = discord.utils.get(member.guild.roles, name="valkyrie_admin")
    admin_role_id = admin_role.id
    role_mention = f"<@&{admin_role_id}>"
    blacklist_file_path = os.path.join(script_directory, 'blacklist.txt')
    if os.path.exists(blacklist_file_path):
        with open(blacklist_file_path, 'r') as blacklist_file:
            blacklist = json.load(blacklist_file)
            if str(member.id) in blacklist:
                channel = discord.utils.get(member.guild.text_channels, name='valkyrie')
                r = ""
                for i in blacklist[str(member.id)]:
                    r += "\n · " + str(i)
                await channel.send(f"{role_mention} User {member.mention} has joined but is blacklisted.\nReasons:\n```{r}\n```")
    
    config = load_config()
    server_id = str(member.guild.id)
    if config[server_id]["user_verification"]:
        await member.send("Welcome to the server. To verify your identity, type the command *verify")
        try:
            # da 60 segundos para responder
            verification_command = await bot.wait_for('message', timeout=60.0, check=lambda message: message.author == member and message.content == '*verify')
        except asyncio.TimeoutError:
            await member.send("You did not verify your identity in time. Please try joining the server later!")
            await member.kick(reason="The user's identity could not be verified in time.")
        else:
            await member.send("Your identity has been verified. Welcome to the server!")
            
    # ahora lo manda en el canal de logs
    channel = discord.utils.get(member.guild.text_channels, name=log_channel)
    embed = discord.Embed(title="New user:", description=f"{member.mention} has joined to the server.", color=discord.Color.green())
    await channel.send(embed=embed)
                
# timeout     
async def timeout_user(*, user_id: int, guild_id: int, until):
    headers = {"Authorization": f"Bot {bot.http.token}"}
    url = f"https://discord.com/api/v9/guilds/{guild_id}/members/{user_id}"
    timeout = (datetime.datetime.utcnow() + datetime.timedelta(minutes=until)).isoformat()
    jsont = {'communication_disabled_until': timeout}
    async with bot.session.patch(url, json=jsont, headers=headers) as session:
        if session.status in range(200, 299):
            return True
        return False

# warn
async def warn_user(ctx, user_id, server_id, reason, server, user, chanel):
    guild = bot.get_guild(server_id)
    if guild is None:
        return "Could not find guild"
    user_id2 = str(user_id)
    server2 = str(server_id)
    reason = str(reason)
    chanel = str(chanel)
    
    warns_file_path = os.path.join(script_directory, 'warns.txt')

    if not os.path.exists(warns_file_path):
        with open(warns_file_path, 'w') as f:
            json.dump({}, f)

    with open(warns_file_path, 'r') as warns_file:
        lwarns = json.load(warns_file)

    lwarns.setdefault(server2, {}).setdefault(user_id2, [])
    lwarns[server2][user_id2].append(reason)
    nwarns = len(lwarns[server2][user_id2])

    if nwarns == 3:
        lwarns[server2].pop(user_id2, None)
        await sancion(user_id, server, reason, chanel, user)
    
    with open(warns_file_path, 'w') as warns_file:
        json.dump(lwarns, warns_file)
    
    user_mention = f'<@{user_id}>'
    await ctx.send(f"{user_mention} you have been warned, reason:\n```\n{reason}\n```")
    print(f"[!] The user {user_id2} has been warned in {server2}, reason: {reason}")
    warns_file.close()

# Comandos de prueba
@bot.command()
async def ping(ctx):
    await ctx.send("pong!")
    
# sanciones
@bot.command()
@commands.has_role('valkyrie_admin')
async def warn(ctx, user: discord.Member, reason: str):
    user_id = user.id
    server_id = ctx.guild.id
    channel = ctx.channel.name
    await warn_user(ctx, user_id, server_id, reason, server_id, user, channel)

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
    user_id = user.id
    await user.ban(reason=reason)
    chanel = discord.utils.get(bot.get_all_channels(), name=admin_channel)
    server = ctx.guild.id
    guild = bot.get_guild(server)
    admin_role = discord.utils.get(guild.roles, name="valkyrie_admin")
    admin_role_id = admin_role.id
    role_mention = f"<@&{admin_role_id}>"
    if chanel is not None:
        await chanel.send(f"[!] The user {user} has been penalized!\nReason: {reason}\nPenalization: ban")
        await chanel.send(f"[!] {role_mention} The user {user} has been banned!")
    sanciones_file_path = os.path.join(script_directory, 'sanciones.txt')

    user_id2 = str(user_id)
    server2 = str(server)
    reason = str(reason)
    
    if not os.path.exists(sanciones_file_path):
        with open(sanciones_file_path, 'w') as f:
            json.dump({}, f)

    with open(sanciones_file_path, 'r') as sanciones_file:
        lsanciones = json.load(sanciones_file)

    channel = discord.utils.get(user.guild.text_channels, name=log_channel)
    embed = discord.Embed(title="Ban:", description=f"{user.mention} has baned by {ctx.author.mention}.", color=discord.Color.red())
    await channel.send(embed=embed)

    lsanciones.setdefault(server2, {}).setdefault(user_id2, [])
    lsanciones[server2][user_id2].append(reason)
    await add_to_blacklist(user_id, lsanciones)

@bot.command()
async def check_sanctions(ctx, user: discord.Member):
    chanel_name = ctx.channel.name
    chanel = discord.utils.get(bot.get_all_channels(), name=chanel_name)
    server_id = ctx.guild.id
    user_id = user.id
    user_mention = f'<@{user_id}>'
    try:
        sanciones_file_path = os.path.join(script_directory, 'sanciones.txt')
        with open(sanciones_file_path, 'r') as sanciones_file:
            lsanciones = json.load(sanciones_file)
            sanciones = lsanciones[str(server_id)][str(user_id)]
            s = "\n"
            for i in sanciones:
                s += i + "\n"
            l = len(sanciones)
            await chanel.send(f"{user_mention} Has {l} sanctions:\n```{s}```")
        sanciones_file.close()
        
    except:
        await chanel.send(f"{user_mention} This user has not been sanctioned!")

@bot.command()
@commands.has_role('valkyrie_admin')
async def clear_sanctions(ctx, user: discord.Member):
    chanel_name = ctx.channel.name
    chanel = discord.utils.get(bot.get_all_channels(), name=chanel_name)
    server_id = ctx.guild.id
    user_id = user.id
    user_mention = f'<@{user_id}>'
    
    sanciones_file_path = os.path.join(script_directory, 'sanciones.txt')

    if not os.path.exists(sanciones_file_path):
        with open(sanciones_file_path, 'w') as f:
            json.dump({}, f)

    with open(sanciones_file_path, 'r') as sanciones_file:
        lsanciones = json.load(sanciones_file)
        
        if str(server_id) in lsanciones:
            if str(user_id) in lsanciones[str(server_id)]:
                del lsanciones[str(server_id)][str(user_id)]
                await chanel.send(f"{user_mention} sanctions have been removed!")
                with open(sanciones_file_path, 'w') as sanciones_file:
                    json.dump(lsanciones, sanciones_file)
                    
            else:
                await chanel.send(f"{user_mention} is not sanctioned!")
        else:
            await chanel.send(f"{user_mention} is not sanctioned!")   
    sanciones_file.close()
    
    channel = discord.utils.get(ctx.guild.text_channels, name=log_channel)
    embed = discord.Embed(title="Sanctions cleaned:", description=f"{user.mention} 's sanctions has cleaned by {ctx.author.mention}.", color=discord.Color.green())
    await channel.send(embed=embed)

@bot.command()
@commands.has_role('valkyrie_admin')
async def banned_members(ctx):
    banned_users = []
    banned_users_id = []
    async for ban_entry in ctx.guild.bans():
        banned_users.append(ban_entry.user.name)
        banned_users_id.append(ban_entry.user.id)
    if len(banned_users) > 0:
        l = ""
        for i, user_name in enumerate(banned_users):
            l += f"\n · {user_name} : {banned_users_id[i]}"
        await ctx.send(f"BANNED USERS:\n```{l}\n```")
    else:
        await ctx.send("There are no banned users!")

@bot.command()
@commands.has_role('valkyrie_admin')
async def unban(ctx, user: discord.User):
    try:
        await ctx.guild.unban(user)
        await ctx.send(f"{user.name} has been unbanned.")
        await remove_from_blacklist(str(user.id))
    except:
        ctx.send("This user is not banned!")
        
    channel = discord.utils.get(ctx.guild.text_channels, name=log_channel)
    embed = discord.Embed(title="Unban:", description=f"{user.mention} has unbaned by {ctx.author.mention}.", color=discord.Color.green())
    await channel.send(embed=embed)

# expulsar de llamada
@bot.command()
@commands.has_role('valkyrie_admin') ######################################### CHECKEAR FUNCIONAMIENTO
async def disconnect(ctx, user: discord.Member):
    voice_state = user.voice

    if voice_state:
        voice_client = await voice_state.channel.connect()
        await user.move_to(None)
        await voice_client.disconnect()
        await ctx.send(f'{user.display_name} has been disconnected!')
        
        channel = discord.utils.get(ctx.guild.text_channels, name=log_channel)
        embed = discord.Embed(title="Disconect:", description=f"{user.mention} has been disconected from voice call by {ctx.author.mention}.", color=discord.Color.red())
        await channel.send(embed=embed)
        
    else:
        await ctx.send(f'{user.display_name} is not on a voice call!')
        
# mute
@bot.command()
@commands.has_role('valkyrie_admin')
async def mute(ctx, user: discord.Member):
    await user.edit(mute=True, deafen=False)
    await ctx.send(f"{user.mention} is muted.")
    
    channel = discord.utils.get(ctx.guild.text_channels, name=log_channel)
    embed = discord.Embed(title="Mute:", description=f"{user.mention} has been muted by {ctx.author.mention}.", color=discord.Color.red())
    await channel.send(embed=embed)
    
@bot.command()
@commands.has_role('valkyrie_admin')
async def unmute(ctx, user: discord.Member):
    await user.edit(mute=False, deafen=False)
    await ctx.send(f"{user.mention} is unmuted, now he or she can speak in voice call!")
    
    channel = discord.utils.get(ctx.guild.text_channels, name=log_channel)
    embed = discord.Embed(title="Unmute:", description=f"{user.mention} has been unmuted by {ctx.author.mention}.", color=discord.Color.green())
    await channel.send(embed=embed)
    
# deafen
@bot.command()
@commands.has_role('valkyrie_admin')
async def deafen(ctx, user: discord.Member):
    await user.edit(mute=False, deafen=True)
    await ctx.send(f"{user.mention} is muted.")
    
    channel = discord.utils.get(ctx.guild.text_channels, name=log_channel)
    embed = discord.Embed(title="Deafen:", description=f"{user.mention} has been deafen by {ctx.author.mention}.", color=discord.Color.red())
    await channel.send(embed=embed)
    
@bot.command()
@commands.has_role('valkyrie_admin')
async def undeafen(ctx, user: discord.Member):
    await user.edit(mute=False, deafen=False)
    await ctx.send(f"{user.mention} is unmuted, now he or she can speak in voice call!")
    
    channel = discord.utils.get(ctx.guild.text_channels, name=log_channel)
    embed = discord.Embed(title="Undeafen:", description=f"{user.mention} has been undeafen by {ctx.author.mention}.", color=discord.Color.green())
    await channel.send(embed=embed)

# server info
@bot.command()
async def server_info(ctx):
    server = ctx.guild

    embed = discord.Embed(title=server.name, description="SERVER INFORMATION", color=0x00ff00)
    embed.add_field(name="Creation date", value=str(server.created_at.strftime("%d/%m/%Y")), inline=False)
    embed.add_field(name="Server owner", value=server.owner.mention, inline=False)
    embed.add_field(name="Number of members", value=server.member_count, inline=False)
    embed.add_field(name="Online members", value=len([m for m in server.members if m.status != discord.Status.offline]), inline=False)
    embed.add_field(name="Roles", value=len(server.roles), inline=False)
    embed.add_field(name="Number of boosts", value=server.premium_subscription_count, inline=False)
    embed.add_field(name="Boost level", value=server.premium_tier, inline=False)

    await ctx.send(embed=embed)

# user info
@bot.command()
async def member_info(ctx, user: discord.Member):
    joined_date = user.joined_at.strftime('%Y-%m-%d %H:%M:%S')
    roles = [role.name for role in user.roles]
    presence = str(user.status)
    activity_str = str(user.activity) if user.activity else "None"

    embed = discord.Embed(title="User information", color=0x00ff00)
    embed.add_field(name="Username", value=user.name, inline=True)
    embed.add_field(name="Server nickname", value=user.nick, inline=True)
    embed.add_field(name="Join date", value=joined_date, inline=False)
    embed.add_field(name="Roles", value=", ".join(roles), inline=False)
    embed.add_field(name="Presence status", value=presence, inline=True)
    embed.add_field(name="Current activity", value=activity_str, inline=False)
    await ctx.send(embed=embed)
    
# delete mesages
@bot.command()
@commands.has_role('valkyrie_admin')
async def delete(ctx, x: int):
    await ctx.channel.purge(limit=x+1)
    
    channel = discord.utils.get(ctx.guild.text_channels, name=log_channel)
    embed = discord.Embed(title="Deletion:", description=f"{ctx.author.mention} has delete {x} messages.", color=discord.Color.yellow())
    await channel.send(embed=embed)

# turn on/off ban blacklisted users
@bot.command()
@commands.has_role('valkyrie_admin')
async def ban_blacklisted_ON(ctx):
    config = load_config()
    server_id = str(ctx.guild.id)
    config[server_id]["ban_blacklisted_users"] = True
    save_config(config)
    await ctx.send(f"Automatic banning has been activated for new blacklisted users!")

@bot.command()
@commands.has_role('valkyrie_admin')
async def ban_blacklisted_OFF(ctx):
    config = load_config()
    server_id = str(ctx.guild.id)
    config[server_id]["ban_blacklisted_users"] = False
    save_config(config)
    await ctx.send(f"Automatic banning has been disabled for new blacklisted users!")

# turn on/off new users verification
@bot.command()
@commands.has_role('valkyrie_admin')
async def new_member_verification_ON(ctx):
    config = load_config()
    server_id = str(ctx.guild.id)
    config[server_id]["user_verification"] = True
    save_config(config)
    await ctx.send(f"Automatic banning has been activated for new blacklisted users!")

@bot.command()
@commands.has_role('valkyrie_admin')
async def new_member_verification_OFF(ctx):
    config = load_config()
    server_id = str(ctx.guild.id)
    config[server_id]["user_verification"] = False
    save_config(config)
    await ctx.send(f"Automatic banning has been disabled for new blacklisted users!")

# help
@bot.command()
async def Help(ctx):
    await ctx.send(str("User guide: https://airilmusic.github.io/Valkyrie-Defender/#"+
                    "\n\nCOMMAND LIST:"+
                    "\n```\n*server_info: displays server information"+
                    "\n*member_info @user: displays information about a user"+
                    "\n*check_sanctions @user: see how many penalties a user has"+
                    "\n*show_badwords: to see server sancioned words list"+
                    "\n*ping: to check if the bot is working "+
                    "\n\nSANCTIONS:"+
                    "\n    1 --> An hour of timeout"+
                    "\n    2 --> A day of timeout"+
                    "\n    3 --> Two days of timeout"+
                    "\n    4 --> A week of timeout"+
                    "\n    5 --> BAN, and this user will be added to a multiserver blacklist\n"+
                    "\nADMIN COMMANDS:"+
                    "\n*delete (num): delete last (num) messages"
                    "\n\n*warn @user reason: this is going to warn a user, 3 warns = 1 sanction"+
                    "\n*ban @user reason: to ban a user (only users with the rol 'valkirye_admin' can execute this command)"+ 
                    "\n*penalize @user reason: to give one penalization to a user (only users with the rol 'valkirye_admin' can execute this command)"+
                    "\n*clear_sanctions @user: to clear all sanctions of a user"+
                    "\n*banned_members: it shows banned user list"+
                    "\n*unban @user: for unban a user"+
                    "\n\n*disconnect @user: for disconnect a user from a voice call"+
                    "\n*mute @user"+
                    "\n*unmute @user"+
                    "\n*deafen @user"+
                    "\n*undeafen @user"+
                    "\n\n*add_badword (word): to add a sanctioned word to the server config"+
                    "\n*remove_badword (word): to remove a word to the sanctioned words list"+
                    "\n\n*ban_blacklisted_ON: to automatically ban blacklisted users"+
                    "\n*ban_blacklisted_OFF: to don't ban automatically blacklisted users"+
                    "\n\n*new_member_verification_ON: to put a verification for new members"+
                    "\n*new_member_verification_OFF: ro remove verification for new members"+
                    "\n```"))

# LOG CHANNEL
@bot.event
async def on_voice_state_update(member, before, after):
    channel = discord.utils.get(member.guild.text_channels, name=log_channel)
    
    if before.channel != after.channel:
        if before.channel:
            channel = discord.utils.get(member.guild.text_channels, name=log_channel)
            embed = discord.Embed(title="Disconection:", description=f"{member.mention} has exit from the voice channel {before.channel.name}.", color=discord.Color.yellow())
            await channel.send(embed=embed)
        if after.channel:
            channel = discord.utils.get(member.guild.text_channels, name=log_channel)
            embed = discord.Embed(title="Conection:", description=f"{member.mention} has join to the voice channel {after.channel.name}.", color=discord.Color.blue())
            await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    channel = discord.utils.get(member.guild.text_channels, name=log_channel)
    embed = discord.Embed(title="Member Leave:", description=f"{member.mention} has leave from the server.", color=discord.Color.red())
    await channel.send(embed=embed)
    
# Easter eggs
# LOS BUSCAIS JEJE UWU

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

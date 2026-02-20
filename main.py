import os, discord, json, asyncio, modules.message_handler, modules.configs
from dotenv import load_dotenv
from pathlib import Path
from discord.utils import get

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)
client.wiped_messages = set()

# --- Helper Functions ---
async def send_as_webhook(channel, name, content, avatar_url=None):
    try:
        webhook = await channel.create_webhook(name=name, avatar=None)
        
        await webhook.send(
            content=content, 
            username=name, 
            avatar_url=avatar_url
        )
        
        await webhook.delete()
        return True
    except discord.Forbidden:
        print(f"Error: Missing 'Manage Webhooks' permission in {channel.name}")
        return False
    except Exception as e:
        print(f"Webhook Error: {e}")
        return False

# --- Event Handlers ---
@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    print(f"WELCOME TO ASTROMECH!")
    for guild in client.guilds:
        bot_member = guild.me
        
        if not bot_member.guild_permissions.administrator:
            try:
                owner = await guild.fetch_member(guild.owner_id)
                owner_mention = owner.mention
            except:
                owner_mention = "Owner"

            warning_msg = (
                f"⚠️ {owner_mention}, {client.user.name} does not have administrator permissions. "
                "Some features may not work properly."
            )
            mods_channel = discord.utils.get(guild.text_channels, name='moderators-only')
            general_channel = discord.utils.get(guild.text_channels, name='general')
            target_channel = mods_channel or general_channel

            if target_channel:
                await target_channel.send(warning_msg)
        
        if "configs" in [channel.name for channel in guild.channels]:
            # client.configs = await modules.configs.load_configs_from_channel(guild, channel_name='configs')
            # print(f"Loaded configurations from 'configs' channel in {guild.name}.")
            
            print("Loading configs from channel is currently disabled. Loading default configurations instead.")
            client.configs = modules.configs.load_configs()
        else: 
            client.configs = modules.configs.load_configs()
            print(f"No configs channel found in {guild.name}. Loaded default configurations.")
  
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('!debug.info'):
        debug_info = f"User: {message.author}\nChannel: {message.channel}\nGuild: {message.guild}"
        await message.channel.send(f"Debug Info:\n{debug_info}")
    # user wipe command, deletes all messages from the user who invoked the command.    
    elif message.content.startswith('!wipe'):
        permissions = message.channel.permissions_for(message.guild.me)
        if not permissions.manage_messages:
            await message.channel.send("Error: Missing 'Manage Messages' permission. Cannot perform wipe.")
            return
        else: 
            async for msg in message.channel.history(limit=None):
                if msg.author == message.author:
                    client.wiped_messages.add(msg.id)
                    await msg.delete()
    elif message.content.startswith('!boom'):
        amount = message.content.replace('!boom', '').strip()
        if amount.isdigit():
            amount = int(amount)
        else:
            amount = 5
        
        if amount > 20:
            await message.channel.send("Please use a lower number.")
            return
        
        for i in range(amount):
            await message.channel.send("@everyone Boom! 💥")
            await asyncio.sleep(0.25)
    elif message.content.startswith('!config.reload'):
        client.configs = modules.configs.load_configs()
        await message.channel.send("Configurations reloaded successfully.")
    elif message.content.startswith('!terminate'):
        configs = client.configs
        
        if (message.author == client.user or any(role.name.lower() in configs["deletionRoleWhitelist"]["guild_staff_roles"] for role in message.author.roles)) or message.author.name.lower() in configs["deletionUserWhitelist"]["whitelisted_users"]:
            content = message.content.replace('!terminate', '').strip()
            if message.mentions:
                member = message.mentions[0]
            else:
                member = get(message.guild.members, name=content) or \
                        get(message.guild.members, display_name=content)

            if member:
                await message.channel.send(f"Terminating {member.display_name}... 💀")
                await member.kick(reason=f"Terminated by {message.author}")
            else:
                await message.channel.send(f"User '{content}' not found.")
        else:
            await message.reply("You do not have permission to use this command.")
    elif message.content.startswith('..bypass'):
        the_message = message
        await message.delete()
        
        if str(the_message.author) == str(the_message.author.display_name):
            await send_as_webhook(
                channel=the_message.channel,
                name=the_message.author,
                content=the_message.content.replace('..bypass', '').strip(),
                avatar_url=the_message.author.avatar.url if the_message.author.avatar else None
            )
        else:
            await send_as_webhook(
                channel=the_message.channel,
                name=str(the_message.author.name) + " (" + str(the_message.author.display_name) + ")",
                content=the_message.content.replace('..bypass', '').strip(),
                avatar_url=the_message.author.avatar.url if the_message.author.avatar else None
            )
    else:
        print("No command, sending to message handler...")
        await modules.message_handler.handle_message(message, client.configs)

@client.event
async def on_member_join(member):
    welcome_channel = discord.utils.get(member.guild.text_channels, name='general')
    if welcome_channel:
        await welcome_channel.send(f'Welcome to the server, {member.mention}!')   
        
@client.event
async def on_message_delete(message):
    permissions = message.channel.permissions_for(message.guild.me)
    configs = client.configs
    
    staff_roles = configs["deletionRoleWhitelist"]["guild_staff_roles"]
    trusted_roles = configs["deletionRoleWhitelist"]["guild_trusted_roles"]
    whitelisted_users = configs["deletionUserWhitelist"]["whitelisted_users"]
    
    whitelisted_roles = {
        r.lower() for r in (staff_roles + trusted_roles)
    }
    
    if message.id in client.wiped_messages:
            client.wiped_messages.remove(message.id)
            return
    
    if permissions.manage_webhooks:
        #                                                                                                                  this errors sometimes idk why but it does and it's only happened once
        if (message.author == client.user or message.author.name.lower() in {u.lower() for u in whitelisted_users} or any(role.name.lower() in whitelisted_roles for role in message.author.roles)): 
            return
        
        logs_channel = discord.utils.get(message.guild.text_channels, name='logs')
        msg_channel = discord.utils.get(message.guild.text_channels, name=message.channel.name)
        if logs_channel:
            await logs_channel.send(f'{message.author.mention}: "{message.content}"')
        
        if msg_channel:
            print(message.author.display_name, message.author, message.author.name)
            
            if str(message.author) == str(message.author.display_name):
                await send_as_webhook(
                    channel=msg_channel,
                    name=str(message.author),
                    content=message.content,
                    avatar_url=message.author.avatar.url if message.author.avatar else None
                )
            else:
                await send_as_webhook(
                    channel=msg_channel,
                    name=str(message.author.name) + " (" + str(message.author.display_name) + ")",
                    content=message.content,
                    avatar_url=message.author.avatar.url if message.author.avatar else None
                )
    else:
        print(f"Warning: Missing 'Manage Webhooks' permission in {message.channel.name}. Falling back to regular message logging.")
        await message.channel.send(f'<{message.author.mention}> "{message.content}"')
        
        
client.run(TOKEN)
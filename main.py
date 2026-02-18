import os, discord, json
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

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

def load_configs():
    configs = {}
    config_path = Path("./configs")

    for file in config_path.glob("*.json"):
        try:
            with file.open("r", encoding="utf-8") as f:
                configs[file.stem] = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error parsing {file.name}: {e}")

    return configs

# --- Event Handlers ---
@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    for guild in client.guilds:
        bot_member = guild.me
        
        '''if not bot_member.guild_permissions.administrator:
            try:
                owner = await guild.fetch_member(guild.owner_id)
                owner_mention = owner.mention
            except:
                owner_mention = "Owner"

            warning_msg = (
                f"⚠️ {owner_mention}, {client.user.name} does not have administrator permissions. "
                "Some features may not work properly."
            )
            mods_channel = discord.utils.get(guild.text_channels, name='moderators')
            general_channel = discord.utils.get(guild.text_channels, name='general')
            target_channel = mods_channel or general_channel

            if target_channel:
                await target_channel.send(warning_msg)'''
        
        if "configs" in [channel.name for channel in guild.channels]:
            client.configs = load_configs() 
        else: 
            client.configs = load_configs()
            print(f"No configs channel found in {guild.name}. Loaded default configurations.")

    
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    #if message.content.startswith('!ping'):
    #    await message.channel.send('Pong!')
        
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
                    await msg.delete()


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
    
    if permissions.manage_webhooks:

        # flags to allow deletion.
        if (message.author == client.user or message.author.name.lower() in {u.lower() for u in whitelisted_users} or any(role.name.lower() in whitelisted_roles for role in message.author.roles)):
            return
        logs_channel = discord.utils.get(message.guild.text_channels, name='logs')
        msg_channel = discord.utils.get(message.guild.text_channels, name=message.channel.name)
        if logs_channel:
            await logs_channel.send(f'{message.author.mention}: "{message.content}"')
        
        if msg_channel:
            await send_as_webhook(
                channel=msg_channel,
                name=str(message.author) + " (" + str(message.author.display_name) + ")",
                content=message.content,
                avatar_url=message.author.avatar.url if message.author.avatar else None
            )
    else:
        print(f"Warning: Missing 'Manage Webhooks' permission in {message.channel.name}. Falling back to regular message logging.")
        await message.channel.send(f'<{message.author.mention}> "{message.content}"')
        
client.run(TOKEN)
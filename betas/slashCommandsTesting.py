import os, discord, json
from dotenv import load_dotenv
from pathlib import Path
from discord.ext import commands
from discord import app_commands

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Using commands.Bot is necessary for Slash Commands
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True # Needed for on_member_join
        super().__init__(command_prefix="!", intents=intents)
        self.wiped_messages = set()
        self.configs = {}

    async def setup_hook(self):
        # This synchronizes your slash commands with Discord
        # Note: In production, syncing globally can take up to an hour. 
        # For testing, you can pass a guild ID to sync instantly.
        await self.tree.sync()
        print(f"Synced slash commands for {self.user}")

    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')
        self.configs = load_configs() # Load configs on startup
        
        for guild in self.guilds:
            if not guild.me.guild_permissions.administrator:
                # Permission warning logic remains similar
                target_channel = discord.utils.get(guild.text_channels, name='moderators') or \
                                 discord.utils.get(guild.text_channels, name='general')
                if target_channel:
                    await target_channel.send(f"⚠️ Warning: Administrator permissions missing.")

bot = MyBot()

# --- Helper Functions ---
async def send_as_webhook(channel, name, content, avatar_url=None):
    try:
        webhook = await channel.create_webhook(name="Logger") # Static name for webhook
        await webhook.send(content=content, username=name, avatar_url=avatar_url)
        await webhook.delete()
        return True
    except Exception as e:
        print(f"Webhook Error: {e}")
        return False

def load_configs():
    configs = {}
    config_path = Path("./configs")
    if not config_path.exists():
        return {"deletionRoleWhitelist": {"guild_staff_roles": [], "guild_trusted_roles": []}, 
                "deletionUserWhitelist": {"whitelisted_users": []}}
    
    for file in config_path.glob("*.json"):
        with file.open("r", encoding="utf-8") as f:
            configs[file.stem] = json.load(f)
    return configs

# --- Slash Commands ---

@bot.tree.command(name="ping", description="Check the bot's latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f'Pong! {round(bot.latency * 1000)}ms')

@bot.tree.command(name="debug_info", description="Get debug information about the current context")
async def debug_info(interaction: discord.Interaction):
    info = (
        f"**User:** {interaction.user}\n"
        f"**Channel:** {interaction.channel.name}\n"
        f"**Guild:** {interaction.guild.name}"
    )
    await interaction.response.send_message(info, ephemeral=True) # Ephemeral means only user sees it

@bot.tree.command(name="wipe", description="Deletes your own recent messages in this channel")
@app_commands.describe(limit="How many messages should I scan? (Max 100)")
async def wipe(interaction: discord.Interaction, limit: int = 100):
    # We still need to defer because deleting multiple messages takes time
    await interaction.response.defer(ephemeral=True)
    
    count = 0
    # Note: The BOT still needs 'Manage Messages' to delete messages 
    # even if they belong to the user, because it's an automated action.
    if not interaction.channel.permissions_for(interaction.guild.me).manage_messages:
        await interaction.followup.send("❌ I (the bot) need 'Manage Messages' permission to do this!")
        return

    async for msg in interaction.channel.history(limit=limit):
        if msg.author == interaction.user:
            bot.wiped_messages.add(msg.id)
            await msg.delete()
            count += 1
    
    await interaction.followup.send(f"✅ Cleaned up {count} of your messages.")

# --- Event Handlers ---

@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name='general')
    if channel:
        await channel.send(f'Welcome to the server, {member.mention}!')

@bot.event
async def on_message_delete(message):
    if message.author.bot or message.id in bot.wiped_messages:
        if message.id in bot.wiped_messages:
            bot.wiped_messages.remove(message.id)
        return

    # Logic for whitelisting and logging
    # (Kept similar to your original logic, using bot.configs)
    conf = bot.configs
    staff = conf.get("deletionRoleWhitelist", {}).get("guild_staff_roles", [])
    trusted = conf.get("deletionRoleWhitelist", {}).get("guild_trusted_roles", [])
    whitelisted_users = conf.get("deletionUserWhitelist", {}).get("whitelisted_users", [])
    
    role_names = {r.name.lower() for r in message.author.roles}
    is_whitelisted = (
        message.author.name.lower() in [u.lower() for u in whitelisted_users] or
        any(role.lower() in role_names for role in (staff + trusted))
    )

    if is_whitelisted:
        return

    logs_channel = discord.utils.get(message.guild.text_channels, name='logs')
    if logs_channel:
        await logs_channel.send(f'**Deleted:** {message.author.mention}: "{message.content}"')

    # Webhook Re-posting logic
    if message.guild.me.guild_permissions.manage_webhooks:
        display_name = f"{message.author.name} ({message.author.display_name})" if message.author.name != message.author.display_name else message.author.name
        avatar = message.author.avatar.url if message.author.avatar else None
        await send_as_webhook(message.channel, display_name, message.content, avatar)

bot.run(TOKEN)
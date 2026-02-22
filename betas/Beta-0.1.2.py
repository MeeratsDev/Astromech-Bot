import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os, discord, json, asyncio, modules.message_handler, modules.configs, modules.leveling, aiosqlite, datetime, discord.errors, re, random as rand
from dotenv import load_dotenv
from pathlib import Path
from discord.utils import get
from discord import app_commands

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


class AstromechClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.wiped_messages = set()
        self.xp_cooldowns = {}
        self.db_path = "./configs/levels.db"
        self.configs = {}

    async def setup_hook(self):
        await self.tree.sync()
        print("Slash commands synced globally.")


client = AstromechClient()


# --- Helper Functions ---
async def send_as_webhook(channel, name, content, avatar_url=None):
    try:
        webhook = await channel.create_webhook(name=name, avatar=None)
        await webhook.send(content=content, username=name, avatar_url=avatar_url)
        await webhook.delete()
        return True
    except discord.Forbidden:
        print(f"Error: Missing 'Manage Webhooks' permission in {channel.name}")
        return False
    except Exception as e:
        print(f"Webhook Error: {e}")
        return False


def is_staff(interaction: discord.Interaction, configs: dict) -> bool:
    staff_roles = configs["deletionRoleWhitelist"]["guild_staff_roles"]
    whitelisted_users = configs["deletionUserWhitelist"]["whitelisted_users"]
    return (
        interaction.user.name.lower() in [u.lower() for u in whitelisted_users]
        or any(role.name.lower() in staff_roles for role in interaction.user.roles)
    )


# --- Event Handlers ---
@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    print("WELCOME TO ASTROMECH!")

    for guild in client.guilds:
        bot_member = guild.me

        if not bot_member.guild_permissions.administrator:
            try:
                owner = await guild.fetch_member(guild.owner_id)
                owner_mention = owner.mention
            except Exception:
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
            print("Loading configs from channel is currently disabled. Loading default configurations instead.")
            client.configs = modules.configs.load_configs()
        else:
            client.configs = modules.configs.load_configs()
            print(f"No configs channel found in {guild.name}. Loaded default configurations.")

    async with aiosqlite.connect("levels.db") as db:
        await db.execute(
            "CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, xp INTEGER, level INTEGER)"
        )
        await db.commit()


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith(client.user.mention) or message.content.startswith(f"<@!{client.user.id}>"):
        response = rand.randint(1, 20)
        replies = [
            "Bleep‑bloop!", "Beep‑beep! Boop‑beep!", "Ee‑oo‑brrt", "Bleep‑bloop‑whistle",
            "Boop‑brrt‑zzt!", "Whirrr‑beep! Zwoop!", "Ee‑bloop‑bzzz‑boop", "Zzt‑whistle‑beep‑bop!",
            "Beep‑whirr‑boop‑ee!", "Bloop‑bzzt‑whistle", "Boop‑ee‑bzzt‑whirr", "Ee‑brrt‑zwoop!",
            "Whistle‑beep‑bzzt‑boop", "Bleep‑whirrr‑zzt!", "Boop‑bzzt‑ee‑whirrr", "Zwoop‑bleep‑brrt",
            "Ee‑whirr‑boop‑bzzt", "Bloop‑zzt‑whistle‑beep!", "Beep‑boop‑ee‑whirr!", "Zzt‑bloop‑boop‑whirr!",
        ]
        await message.reply(replies[response - 1])
    else:
        print("No command, sending to message handler...")
        await modules.message_handler.handle_message(message, client.configs, client)


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

    whitelisted_roles = {r.lower() for r in (staff_roles + trusted_roles)}

    if message.id in client.wiped_messages:
        client.wiped_messages.remove(message.id)
        return

    if permissions.manage_webhooks:
        if (
            message.author == client.user
            or message.author.name.lower() in {u.lower() for u in whitelisted_users}
            or any(role.name.lower() in whitelisted_roles for role in message.author.roles)
        ):
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
                    avatar_url=message.author.avatar.url if message.author.avatar else None,
                )
            else:
                await send_as_webhook(
                    channel=msg_channel,
                    name=f"{message.author.name} ({message.author.display_name})",
                    content=message.content,
                    avatar_url=message.author.avatar.url if message.author.avatar else None,
                )
    else:
        print(f"Warning: Missing 'Manage Webhooks' permission in {message.channel.name}. Falling back to regular message logging.")
        await message.channel.send(f'<{message.author.mention}> "{message.content}"')


# --- Slash Commands ---

@client.tree.command(name="debug_info", description="Show debug information about the current context.")
async def debug_info(interaction: discord.Interaction):
    info = (
        f"**User:** {interaction.user}\n"
        f"**Channel:** {interaction.channel}\n"
        f"**Guild:** {interaction.guild}"
    )
    await interaction.response.send_message(f"Debug Info:\n{info}", ephemeral=True)


@client.tree.command(name="wipe", description="Delete all of your messages in this channel.")
async def wipe(interaction: discord.Interaction):
    permissions = interaction.channel.permissions_for(interaction.guild.me)
    if not permissions.manage_messages:
        await interaction.response.send_message(
            "Error: Missing 'Manage Messages' permission. Cannot perform wipe.", ephemeral=True
        )
        return

    await interaction.response.send_message("Wiping your messages...", ephemeral=True)

    async for msg in interaction.channel.history(limit=None):
        if msg.author == interaction.user:
            client.wiped_messages.add(msg.id)
            await msg.delete()


@client.tree.command(name="boom", description="Spam a message @everyone a number of times.")
@app_commands.describe(
    amount="Number of times to send (max 20)",
    message="Message to send (default: Boom! 💥)"
)
async def boom(interaction: discord.Interaction, amount: int = 5, message: str = "Boom! 💥"):
    if amount > 20:
        await interaction.response.send_message("Please use a lower number.", ephemeral=True)
        return

    await interaction.response.send_message("Boom incoming! 💥", ephemeral=True)

    for _ in range(amount):
        await interaction.channel.send(f"@everyone {message}")
        await asyncio.sleep(0.25)


@client.tree.command(name="config_reload", description="Reload bot configurations.")
async def config_reload(interaction: discord.Interaction):
    client.configs = modules.configs.load_configs()
    await interaction.response.send_message("Configurations reloaded successfully.", ephemeral=True)


@client.tree.command(name="terminate", description="Kick a member from the server.")
@app_commands.describe(member="The member to kick")
async def terminate(interaction: discord.Interaction, member: discord.Member):
    configs = client.configs

    if not is_staff(interaction, configs):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    await interaction.response.send_message(f"Deactivating {member.display_name}... 💀")
    await member.kick(reason=f"Terminated by {interaction.user}")


@client.tree.command(name="bypass", description="Send a message as yourself via webhook (bypasses display name).")
@app_commands.describe(content="The message content to send")
async def bypass(interaction: discord.Interaction, content: str):
    await interaction.response.send_message("Sending...", ephemeral=True)

    user = interaction.user
    if str(user) == str(user.display_name):
        name = str(user)
    else:
        name = f"{user.name} ({user.display_name})"

    await send_as_webhook(
        channel=interaction.channel,
        name=name,
        content=content,
        avatar_url=user.avatar.url if user.avatar else None,
    )


@client.tree.command(name="shutdown", description="Shut down the bot (owner only).")
async def shutdown(interaction: discord.Interaction):
    if interaction.user.name != "meerats":
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    await interaction.response.send_message("Shutting down... 👋", ephemeral=True)
    await on_shutdown()
    await client.close()


@client.tree.command(name="mute", description="Timeout a member for 10 minutes.")
@app_commands.describe(member="The member to mute")
async def mute(interaction: discord.Interaction, member: discord.Member):
    configs = client.configs

    if not is_staff(interaction, configs):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    try:
        await interaction.response.send_message(f"Putting restraining bolt on {member.display_name}... 🤐")
        await member.timeout(datetime.timedelta(minutes=10))
    except discord.errors.Forbidden:
        await interaction.followup.send("I don't have permission to timeout that user.", ephemeral=True)


@client.tree.command(name="checkrank", description="Check your current rank/level.")
async def checkrank(interaction: discord.Interaction):
    rank = await modules.leveling.get_user_level(interaction.user.id, client.db_path, client.configs)
    await interaction.response.send_message(f"Your current rank is: {rank}", ephemeral=True)


# --- Shutdown Helper ---
async def on_shutdown():
    for guild in client.guilds:
        moderators_channel = discord.utils.get(guild.text_channels, name='moderators-only')
        general_channel = discord.utils.get(guild.text_channels, name='general')
        target_channel = moderators_channel or general_channel

        if target_channel:
            warning_msg = (
                f"⚠️ {client.user.name} is shutting down. "
                "Some features may not work properly until the bot is back online."
            )
            try:
                await target_channel.send(warning_msg)
            except Exception as e:
                print(f"Failed to send shutdown warning to channel {target_channel.name}: {e}")


client.run(TOKEN)
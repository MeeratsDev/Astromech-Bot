import os, discord, json, asyncio
from dotenv import load_dotenv
from pathlib import Path
from discord.ext import commands
from discord import app_commands

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# --- Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
bot.wiped_messages = set()  # Track wiped messages to prevent re-logging


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


async def load_configs_from_channel(guild, channel_name='configs'):
    configs = {}
    configs_channel = discord.utils.get(guild.text_channels, name=channel_name)
    if configs_channel:
        try:
            async for message in configs_channel.history(limit=100):
                if message.attachments:
                    attachment = message.attachments[0]
                    if attachment.filename.endswith('.json'):
                        file_content = await attachment.read()
                        try:
                            config_data = json.loads(file_content)
                            config_name = attachment.filename[:-5]
                            configs[config_name] = config_data
                        except json.JSONDecodeError as e:
                            print(f"Error parsing {attachment.filename}: {e}")
                    else:
                        print(f"Skipping {attachment.filename}: Not a JSON file.")
                else:
                    print(f"Skipping message {message.id}: No attachments found.")
        except Exception as e:
            print(f"Error loading configs from channel: {e}")
    return configs


# --- Events ---
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print("Welcome to Astromech Beta 0.1.1")
    print("this is an experimental version of Astromech with slash commands.")
    print("It is a direct translation by Claude of the original codebase, so some features may not work as expected.")

    for guild in bot.guilds:
        bot_member = guild.me

        if not bot_member.guild_permissions.administrator:
            try:
                owner = await guild.fetch_member(guild.owner_id)
                owner_mention = owner.mention
            except Exception:
                owner_mention = "Owner"

            warning_msg = (
                f"⚠️ {owner_mention}, {bot.user.name} does not have administrator permissions. "
                "Some features may not work properly."
            )
            mods_channel = discord.utils.get(guild.text_channels, name='moderators')
            general_channel = discord.utils.get(guild.text_channels, name='general')
            target_channel = mods_channel or general_channel
            if target_channel:
                await target_channel.send(warning_msg)

        if any(ch.name == 'configs' for ch in guild.channels):
            bot.configs = await load_configs_from_channel(guild, channel_name='configs')
            print(f"Loaded configurations from 'configs' channel in {guild.name}.")
        else:
            bot.configs = load_configs()
            print(f"No configs channel found in {guild.name}. Loaded default configurations.")

    # Sync slash commands globally
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s).")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


@bot.event
async def on_member_join(member):
    welcome_channel = discord.utils.get(member.guild.text_channels, name='general')
    if welcome_channel:
        await welcome_channel.send(f'Welcome to the server, {member.mention}!')


@bot.event
async def on_message_delete(message):
    if message.guild is None:
        return

    permissions = message.channel.permissions_for(message.guild.me)
    configs = bot.configs

    staff_roles = configs["deletionRoleWhitelist"]["guild_staff_roles"]
    trusted_roles = configs["deletionRoleWhitelist"]["guild_trusted_roles"]
    whitelisted_users = configs["deletionUserWhitelist"]["whitelisted_users"]

    whitelisted_roles = {r.lower() for r in (staff_roles + trusted_roles)}

    if message.id in bot.wiped_messages:
        bot.wiped_messages.remove(message.id)
        return

    if message.author == bot.user:
        return

    if (
        message.author.name.lower() in {u.lower() for u in whitelisted_users}
        or any(role.name.lower() in whitelisted_roles for role in message.author.roles)
    ):
        return

    logs_channel = discord.utils.get(message.guild.text_channels, name='logs')
    msg_channel = discord.utils.get(message.guild.text_channels, name=message.channel.name)

    if logs_channel:
        await logs_channel.send(f'{message.author.mention}: "{message.content}"')

    if permissions.manage_webhooks and msg_channel:
        print(message.author.display_name, message.author, message.author.name)

        if str(message.author) == str(message.author.display_name):
            webhook_name = str(message.author)
        else:
            webhook_name = f"{message.author.name} ({message.author.display_name})"

        await send_as_webhook(
            channel=msg_channel,
            name=webhook_name,
            content=message.content,
            avatar_url=message.author.avatar.url if message.author.avatar else None
        )
    else:
        print(f"Warning: Missing 'Manage Webhooks' permission in {message.channel.name}. Falling back to regular message logging.")
        if msg_channel:
            await msg_channel.send(f'<{message.author.mention}> "{message.content}"')


# --- Prefix Commands (kept for backwards compatibility) ---
@bot.command(name='debug.info')
async def debug_info(ctx):
    """Show debug info about the current context."""
    info = f"User: {ctx.author}\nChannel: {ctx.channel}\nGuild: {ctx.guild}"
    await ctx.send(f"Debug Info:\n{info}")


@bot.command(name='config.reload')
async def config_reload(ctx):
    """Reload configurations from disk."""
    bot.configs = load_configs()
    await ctx.send("Configurations reloaded successfully.")


# --- Slash Commands ---
@bot.tree.command(name="debug_info", description="Show debug info about the current context.")
async def slash_debug_info(interaction: discord.Interaction):
    info = f"User: {interaction.user}\nChannel: {interaction.channel}\nGuild: {interaction.guild}"
    await interaction.response.send_message(f"Debug Info:\n{info}", ephemeral=True)


@bot.tree.command(name="wipe", description="Delete all of your messages in this channel.")
async def slash_wipe(interaction: discord.Interaction):
    permissions = interaction.channel.permissions_for(interaction.guild.me)
    if not permissions.manage_messages:
        await interaction.response.send_message(
            "Error: Missing 'Manage Messages' permission. Cannot perform wipe.", ephemeral=True
        )
        return

    await interaction.response.send_message("Wiping your messages...", ephemeral=True)
    async for msg in interaction.channel.history(limit=None):
        if msg.author == interaction.user:
            bot.wiped_messages.add(msg.id)
            await msg.delete()


@bot.tree.command(name="boom", description="Send a burst of Boom messages.")
@app_commands.describe(amount="Number of booms to send (default: 5)")
async def slash_boom(interaction: discord.Interaction, amount: int = 5):
    await interaction.response.send_message(f"Sending {amount} booms! 💥", ephemeral=True)
    for _ in range(amount):
        await interaction.channel.send("Boom! 💥")
        await asyncio.sleep(0.25)


@bot.tree.command(name="config_reload", description="Reload bot configurations.")
async def slash_config_reload(interaction: discord.Interaction):
    bot.configs = load_configs()
    await interaction.response.send_message("Configurations reloaded successfully.", ephemeral=True)


@bot.tree.command(name="terminate", description="Kick a user from the server.")
@app_commands.describe(member="The member to kick")
async def slash_terminate(interaction: discord.Interaction, member: discord.Member):
    configs = bot.configs
    allowed_roles = configs["deletionRoleWhitelist"]["guild_staff_roles"]

    is_staff = any(role.name.lower() in allowed_roles for role in interaction.user.roles)
    if not is_staff:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    await interaction.response.send_message(f"Terminating {member.display_name}... 💀")
    await member.kick(reason=f"Terminated by {interaction.user}")


bot.run(TOKEN)
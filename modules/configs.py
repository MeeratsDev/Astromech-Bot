import json, discord
from pathlib import Path

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
            
def load_member_configs(guild):
    member_configs = {}
    for member in guild.members:
        member_configs[str(member.id)] = {
            "xp": 0,
            "level": 1,
            "last_message_time": None
        }
    return member_configs
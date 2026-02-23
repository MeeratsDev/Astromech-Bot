import re, modules.leveling as leveling

def contains_blocked_pattern(text, configs):
    try:
        print("configs loads:", configs.keys())
    except Exception as e:
        print(f"Error loading configs: {e}")
        configs = {"blockedFormats": {"blocked_patterns": {}}}
    
    for name, pattern in configs["blockedFormats"]["blocked_patterns"].items():
        if re.search(pattern["regex"], text, re.IGNORECASE):
            return True, name
    return False, None

async def handle_message(message, configs, client=None):
    blocked, pattern_name = contains_blocked_pattern(message.content, configs)

    if blocked:
        print(f"Message by {message.author} matched blocked pattern: {pattern_name}. Deleting message.")
        await message.delete()
        await message.channel.send(
            f"{message.author.mention}, your message was removed for: {pattern_name}."
        )
    else:
        await leveling.level(message, client.db_path, client.xp_cooldowns)
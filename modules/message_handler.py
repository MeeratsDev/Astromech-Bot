import re, discord, random, aiosqlite, modules.leveling as leveling

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
    print(f"Received message: '{message.content}' from {message.author}")
    blocked, pattern_name = contains_blocked_pattern(message.content, configs)
    print(f"Blocked: {blocked}, Pattern Name: {pattern_name}")

    if blocked:
        print(f"Message matched blocked pattern: {pattern_name}. Deleting message.")
        await message.delete()
        await message.channel.send(
            f"{message.author.mention}, your message was removed (matched: {pattern_name})."
        )
    else:
        await leveling.level(message, client.db_path, client.xp_cooldowns)
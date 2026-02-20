import re

def contains_blocked_pattern(text, configs):
    try:
        print("configs loads:", configs.keys())
    except Exception as e:
        print(f"Error loading configs: {e}")
        configs = {"blockedFormats": {"blocked_patterns": {}}}
    
    for name, pattern in configs["blockedFormats"]["blocked_patterns"].items():
        if re.search(pattern["regex"], text.lower()):
            return True, name
    return False, None

async def handle_message(message, configs):
    blocked, pattern_name = contains_blocked_pattern(message.content, configs)

    if blocked:
        await message.delete()
        await message.channel.send(
            f"{message.author.mention}, your message was removed (matched: {pattern_name})."
        )
    else:
        pass
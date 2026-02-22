import random, aiosqlite

async def level(message, db, xp_cooldowns):
    if message.author.bot or not message.guild:
        return

    user_id = message.author.id

    current_time = message.created_at.timestamp()
    if user_id not in xp_cooldowns or (current_time - xp_cooldowns[user_id]) > 60:
        async with aiosqlite.connect("levels.db") as db:
            async with db.execute("SELECT xp, level FROM users WHERE user_id = ?", (user_id,)) as cursor:
                result = await cursor.fetchone()
                
                if result is None:
                    xp, level = 0, 0
                    await db.execute("INSERT INTO users (user_id, xp, level) VALUES (?, ?, ?)", (user_id, xp, level))
                else:
                    xp, level = result

            # Add XP and check for level up
            xp += random.randint(15, 25)
            next_lvl_xp = 5 * (level**2) + (50 * level) + 100

            if xp >= next_lvl_xp:
                level += 1
                await message.channel.send(f"Congrats {message.author.mention}! You reached **Level {level}**!")

            await db.execute("UPDATE users SET xp = ?, level = ? WHERE user_id = ?", (xp, level, user_id))
            await db.commit()
            xp_cooldowns[user_id] = current_time
    
async def get_user_level(user_id, db, configs):
    async with aiosqlite.connect(db) as db:
        async with db.execute("SELECT xp, level FROM users WHERE user_id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()
            if result is None:
                return 0, 0
            elif result:
                if result in configs["levels"]["level_ranks"]:
                    return result in configs["levels"]["level_ranks"]
                else:
                    return
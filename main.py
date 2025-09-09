# main.py
import discord
from discord.ext import commands
import os
import json
from flask import Flask
from threading import Thread
import datetime
import random

# ------------------- Settings -------------------
FATHER_ID = "YOUR_DISCORD_ID_HERE"

# ------------------- Keep Alive -------------------
app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run():
    app.run(host='0.0.0.0', port=5000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ------------------- Data Storage -------------------
DATA_FILE = "data.json"

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
else:
    data = {"users": {}}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ------------------- Helper Functions -------------------
DAY_ORDER = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

def calculate_free_slots(busy_times, play_times):
    day_start, day_end = 0, 24*60
    busy_ranges = []
    for b in busy_times:
        start, end = map(int, b.split("-"))
        busy_ranges.append((start*60, end*60))
    busy_ranges.sort()
    
    free_ranges = []
    current = day_start
    for start, end in busy_ranges:
        if current < start:
            free_ranges.append((current, start))
        current = max(current, end)
    if current < day_end:
        free_ranges.append((current, day_end))
    
    # Intersect with playtime
    if play_times:
        play_ranges = []
        for p in play_times:
            start, end = map(int, p.split("-"))
            play_ranges.append((start*60, end*60))
        final_free = []
        for fs, fe in free_ranges:
            for ps, pe in play_ranges:
                s = max(fs, ps)
                e = min(fe, pe)
                if s < e:
                    final_free.append((s, e))
        free_ranges = final_free
    
    free_slots = [f"{s//60}-{e//60}" for s, e in free_ranges]
    return free_slots

def mutual_free(users, day):
    """Calculate mutual free slots for a list of user IDs on a given day"""
    all_free = None
    for user_id in users:
        schedule = data["users"][user_id].get("schedule", [])
        playtime = data["users"][user_id].get("playtime", [])
        busy_times = [s["time"] for s in schedule if s["day"] == day]
        play_times_today = [p["time"] for p in playtime if p["day"] == day]
        free_slots = calculate_free_slots(busy_times, play_times_today)
        free_set = set(free_slots)
        if all_free is None:
            all_free = free_set
        else:
            all_free = all_free & free_set
    return sorted(list(all_free)) if all_free else []

# ------------------- Discord Bot -------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # Determine name logic
    user_id = str(message.author.id)
    if user_id == FATHER_ID:
        name = "Father"
    else:
        name = message.author.mention

    content_lower = message.content.lower()
    
    # Respond to greetings
    greetings = ["hello", "hi", "hey"]
    if any(greet in content_lower for greet in greetings):
        await message.channel.send(f"Hello {name}! I'm alive 🚀")
        return

    if bot.user in message.mentions or "slopy" in content_lower:
        content = message.content.replace(f"<@{bot.user.id}>", "").strip().lower()

        # -------- PLAY command --------
        if content.startswith("play"):
            game_name = content[4:].strip()
            if not game_name:
                await message.channel.send(f"⚠️ Please specify a game, {name}.")
                return
            user = data["users"].setdefault(user_id, {"schedule": [], "playtime": [], "games": []})
            user["games"].append(game_name)
            save_data()
            await message.channel.send(f"✅ Game '{game_name}' added for {name}!")

        # -------- BUSY command --------
        elif content.startswith("busy"):
            parts = content.split(maxsplit=3)
            if len(parts) < 4:
                await message.channel.send(f"⚠️ Format: `@SLOPY busy <type> <day(s)> <time>`, {name}")
                return
            busy_type = parts[1]
            days = parts[2].split("-")
            busy_time = parts[3]
            user = data["users"].setdefault(user_id, {"schedule": [], "playtime": [], "games": []})
            start_idx = DAY_ORDER.index(days[0].capitalize())
            end_idx = DAY_ORDER.index(days[-1].capitalize())
            for i in range(start_idx, end_idx+1):
                user["schedule"].append({"day": DAY_ORDER[i], "type": busy_type, "time": busy_time})
            save_data()
            await message.channel.send(f"✅ {busy_type.capitalize()} schedule {parts[2]} {busy_time} added for {name}!")

        # -------- PLAYTIME command --------
        elif content.startswith("playtime"):
            parts = content.split(maxsplit=2)
            if len(parts) < 3:
                await message.channel.send(f"⚠️ Format: `@SLOPY playtime <day> <time>`, {name}")
                return
            day = parts[1].capitalize()
            time_range = parts[2]
            user = data["users"].setdefault(user_id, {"schedule": [], "playtime": [], "games": []})
            user["playtime"].append({"day": day, "time": time_range})
            save_data()
            await message.channel.send(f"✅ Playtime {day} {time_range} added for {name}!")

        # -------- FREE command --------
        elif "free" in content:
            targets = [u for u in message.mentions if u != bot.user]
            if not targets:
                await message.channel.send(f"⚠️ Please mention the user(s) to check, {name}.")
                return

            target_ids = [str(u.id) for u in targets]
            for tid in target_ids:
                if tid not in data["users"]:
                    await message.channel.send(f"⚠️ No schedule found for <@{tid}>.")
                    return

            today = DAY_ORDER[datetime.datetime.today().weekday()]
            free_slots = mutual_free(target_ids, today)

            if free_slots:
                response = f"Mutual free time today: {', '.join(free_slots)}."
                games = []
                for tid in target_ids:
                    games += data["users"][tid].get("games", [])
                if games:
                    response += f" Suggested game: {random.choice(games)} 🎮"
            else:
                response = "No mutual free time available today. 😅"
            await message.channel.send(response)

        # -------- SUGGEST GAME command --------
        elif "suggest game" in content:
            all_games = []
            for u in data["users"].values():
                all_games += u.get("games", [])
            if all_games:
                await message.channel.send(f"🎲 How about playing: {random.choice(all_games)}?")
            else:
                await message.channel.send("No games have been suggested yet!")

# ------------------- Start Bot -------------------
keep_alive()
bot.run(os.environ["TOKEN"])

from flask import Flask
from threading import Thread
import discord
from discord.ext import commands
import os

# --- Keep Alive Webserver ---
app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- Discord Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello {ctx.author.mention}! I'm alive 🚀")

# --- Start bot ---
keep_alive()
bot.run(os.environ["TOKEN"])

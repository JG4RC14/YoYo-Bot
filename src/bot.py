import os
import discord
from discord.ext import commands
from dotenv import load_dotenv


# Load environment variables from .env
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN not found in environment variables. Please set it in the .env file.")

# Configure Discord intents
intents = discord.Intents.default()


# Create bot instance
bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# Runs when the bot successfully connects to Discord
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print("Bot is ready!")


# Start the bot
bot.run(TOKEN)
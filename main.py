from pymongo import MongoClient
import nextcord
from nextcord.ext import commands
import requests
import asyncio
import dotenv
import os

dotenv.load_dotenv()

BOT_TOKEN=os.environ['BOT_TOKEN'] # discord bot token
DB_URI=os.environ['DB_URI'] # mongodb cluster url

connetion = MongoClient(DB_URI)
db = connetion['repobot-db']
t_guilds = db['guilds']

bot = commands.Bot("/", intents=nextcord.Intents.all())

class add_project_emb(nextcord.Embed):
    def __init__(self):
        super().__init__(title="adding project...", description="adding project to watch list", color=0x0092ed)

@bot.event
async def on_ready():
    print(f"logged in as {bot.user}, ID = {bot.user.id}")

@bot.event
async def on_guild_join(guild: nextcord.Guild):
    t_guilds.insert_one({"id": str(guild.id), "repos": []})

@bot.slash_command("add-project", "add new project to watch")
async def add_project(interaction: nextcord.Interaction, repo: str = nextcord.SlashOption(required=True, description="url of repository (HTTPS)")):
    pass

bot.run(BOT_TOKEN)
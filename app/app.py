import discord
from discord.ext import commands
import logging
import os
from dotenv import load_dotenv
from client.openrouter import OPENROUTER_CLIENT
from client.database import init_db, Session, Servers
from config import BASE_SYSTEM_PROMPT, BASE_MODEL

logger = logging.getLogger('discord')
    
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")

BASE_DIR = os.getcwd()

cogs = [
    "chat",
    "settings",
]

async def load(bot: commands.Bot):
    logger.info("Loading commands")
    for cog in cogs:
        await bot.load_extension(f'commands.{cog}')

    @bot.tree.command(name="sync")
    async def sync(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        # only for owner of bot
        if interaction.user.id != bot.owner_id:
            await interaction.followup.send("You are not the owner of this bot!", ephemeral=True)
            return
        try:
            synced = await bot.tree.sync()
            await interaction.followup.send(f"Done. [{', '.join([app.name for app in synced])}]", ephemeral=True)
        except: 
            await interaction.followup.send("Something went wrong!", ephemeral=True)

    logger.info("Loading database")
    init_db() 

    for guild in bot.guilds:
        db_guild = Session.get(Servers,str(guild.id))
        # if it's a new server
        if not db_guild:
            Session.add(Servers(server_id=str(guild.id), server_name=guild.name))
            Session.commit()
            # read it again
            db_guild = Session.get(Servers,str(guild.id))

        # fix for existing servers
        changed = False
        if not db_guild.model:
            changed = True
            db_guild.model = BASE_MODEL
        if not db_guild.system_prompt:
            changed = True
            db_guild.system_prompt = BASE_SYSTEM_PROMPT
        if changed:
            Session.commit()
    OPENROUTER_CLIENT.set_client(OPENROUTER_KEY)

if __name__ == "__main__":
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix=".", intents=intents)

    @bot.event
    async def on_ready():
        await load(bot)
        await bot.tree.sync()
        logger.info("Mayo ready")
        

    bot.run(DISCORD_TOKEN)

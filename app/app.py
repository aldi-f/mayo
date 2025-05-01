import discord
from discord.ext import commands
import logging
import os
from dotenv import load_dotenv
from app.client.openrouter import OPENROUTER_CLIENT
from app.config import 
from database import Servers, init_db, Session
from configurations import SERVER_CONFIGURATIONS, OPENAI_CLIENT, SYSTEM_PROMPT, DEEPSEEK_CLIENT, OPENROUTER_CLIENT

logger = logging.getLogger('discord')
    
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")

BASE_DIR = os.getcwd()

cogs = [
    "chat",
]

async def load(bot: commands.Bot):
    logger.info("Loading commands")
    for cog in cogs:
        await bot.load_extension(f'commands.{cog}')

    @bot.tree.command(name="sync")
    async def func(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            await bot.tree.sync()
            await interaction.followup.send(f"Done. [{', '.join([app.name for app in commands])}]", ephemeral=True)
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
        configs = db_guild.configurations
        if not db_guild.configurations.get("gpt_system_prompt"):
            changed = True
            configs["gpt_system_prompt"] = SYSTEM_PROMPT
        if not db_guild.configurations.get("deepseek_system_prompt"):
            changed = True
            configs["deepseek_system_prompt"] = SYSTEM_PROMPT
        if changed:
            db_guild.configurations = { **configs}
            Session.commit()
        SERVER_CONFIGURATIONS.update_server_configurations(str(guild.id), db_guild.configurations)
    OPENROUTER_CLIENT.set_client(OPENROUTER_KEY)






# when importing something from mustard.py in another file, it will rerun bot.run()
# this takes care of it
if __name__ == "__main__":
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix=".", intents=intents)

    @bot.event
    async def on_ready():
        await load(bot)
        logger.info(f"Loaded commands: [{', '.join([app.name for app in commands])}]")
        logger.info("Mayo ready")


    bot.run(DISCORD_TOKEN)

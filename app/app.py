import discord
from discord.ext import commands
import logging
import os
from client.openrouter import OPENROUTER_CLIENT
from client.database import get_or_create_server, init_db
from config import settings

logger = logging.getLogger('discord')


BASE_DIR = os.getcwd()

cogs = [
    "chat",
    "settings",
    "grok_check",
]

async def load(bot: commands.Bot):
    logger.info("Loading commands")
    for cog in cogs:
        await bot.load_extension(f'commands.{cog}')

    @bot.tree.command(name="sync")
    async def sync(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if interaction.user.id != bot.owner_id:
            await interaction.followup.send("You are not the owner of this bot!", ephemeral=True)
            return
        try:
            if settings.GUILD_ID:
                guild = discord.Object(id=settings.GUILD_ID)
                bot.tree.copy_global_to(guild=guild)
                synced = await bot.tree.sync(guild=guild)
            else:
                synced = await bot.tree.sync()
            await interaction.followup.send(
                f"Done. [{', '.join([app.name for app in synced])}]", ephemeral=True
            )
        except Exception as e:
            logger.error(f"Sync error: {e}")
            await interaction.followup.send("Something went wrong!", ephemeral=True)

    logger.info("Loading database")
    init_db()

    for guild in bot.guilds:
        get_or_create_server(str(guild.id))

    OPENROUTER_CLIENT.set_client(settings.OPENROUTER_API_KEY)

if __name__ == "__main__":
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix=settings.COMMAND_PREFIX, intents=intents)

    @bot.event
    async def on_ready():
        await load(bot)
        if settings.GUILD_ID:
            guild = discord.Object(id=settings.GUILD_ID)
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
        else:
            await bot.tree.sync()
        logger.info("Mayo ready")

    bot.run(settings.DISCORD_TOKEN)

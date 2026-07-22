import discord
import aiohttp
from discord import app_commands
from discord.ext import commands
from client.database import Session, Servers, UserSettings, get_or_create_user
from config import settings

SERVER_SETTINGS_FIELDS = [
    ("chat_model", "```{value}```"),
    ("chat_system_prompt", "```{value}```"),
    ("chat_temperature", "```{value}```"),
    ("chat_total_cost", "```${value:.4f}```"),
]

USER_SETTINGS_FIELDS = SERVER_SETTINGS_FIELDS + [
    ("grok_model", "```{value}```"),
    ("grok_system_prompt", "```{value}```"),
    ("grok_temperature", "```{value}```"),
    ("grok_total_cost", "```${value:.4f}```"),
]


def _build_settings_embed(obj, fields, title, color, description=None) -> discord.Embed:
    embed = discord.Embed(title=title, color=color, description=description)
    for attr, fmt in fields:
        value = getattr(obj, attr)
        embed.add_field(name=attr, value=fmt.format(value=value), inline=False)
    return embed


class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="settings", invoke_without_command=True)
    @commands.is_owner()
    async def settings(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            with Session() as session:
                server = session.get(Servers, str(ctx.guild.id))
                if server:
                    embed = _build_settings_embed(
                        server, SERVER_SETTINGS_FIELDS, "Server Settings", discord.Color.blue(),
                        "Use `.settings chat_model|chat_system_prompt|chat_temperature` to change settings",
                    )
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("Server not found in database.")

    @settings.command(name="chat_model")
    @commands.is_owner()
    async def set_chat_model(self, ctx, *, model: str):
        if not model:
            await ctx.send("Please provide a model name.")
            return

        async with aiohttp.ClientSession() as session:
            async with session.get("https://openrouter.ai/api/v1/models") as resp:
                data = await resp.json()
        available_models = [m["id"] for m in data["data"]]
        if model not in available_models:
            await ctx.send("Invalid model name.")
            return

        with Session() as session:
            server = session.get(Servers, str(ctx.guild.id))
            server.chat_model = model
            session.commit()
        await ctx.send(f"Chat model updated to `{model}`!")

    @settings.command(name="chat_system_prompt")
    @commands.is_owner()
    async def set_chat_system_prompt(self, ctx, *, prompt: str):
        if not prompt:
            await ctx.send("Please provide a system prompt.")
            return

        with Session() as session:
            server = session.get(Servers, str(ctx.guild.id))
            server.chat_system_prompt = prompt
            session.commit()
        await ctx.send("Chat system prompt updated!")

    @settings.command(name="chat_temperature")
    @commands.is_owner()
    async def set_chat_temperature(self, ctx, *, temperature: float):
        if temperature < 0.0 or temperature > 2.0:
            await ctx.send("Temperature must be between 0.0 and 2.0.")
            return

        with Session() as session:
            server = session.get(Servers, str(ctx.guild.id))
            server.chat_temperature = temperature
            session.commit()
        await ctx.send(f"Chat temperature updated to `{temperature}`!")

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("Only bot owner can use this command.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("Invalid value. Check the expected type.")
        else:
            raise error

    @app_commands.command(name="settings", description="Show or set your personal settings")
    @app_commands.describe(
        chat_model="Set your preferred chat model",
        chat_prompt="Set your system prompt",
        chat_temperature="Set chat temperature (0.0 - 2.0)",
        grok_model="Set your Grok fact-check model",
        grok_prompt="Set your Grok system prompt",
        grok_temperature="Set Grok temperature (0.0 - 2.0)",
        user_id="View or edit another user's settings (bot owner only)",
    )
    @app_commands.allowed_installs(users=True, guilds=False)
    async def user_settings(
        self,
        interaction: discord.Interaction,
        chat_model: str | None = None,
        chat_prompt: str | None = None,
        chat_temperature: float | None = None,
        grok_model: str | None = None,
        grok_prompt: str | None = None,
        grok_temperature: float | None = None,
        user_id: str | None = None,
    ):
        target_id = user_id or str(interaction.user.id)
        if user_id and not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message(
                "Only bot owner can view other users' settings.", ephemeral=True
            )
            return

        get_or_create_user(target_id)

        if user_id:
            try:
                target_user = await self.bot.fetch_user(int(target_id))
                title = f"{target_user.name}'s Settings"
            except Exception:
                title = f"User {target_id}'s Settings"
        else:
            title = "Your Settings"

        with Session() as session:
            user = session.get(UserSettings, target_id)

            updated = False
            if chat_model is not None:
                user.chat_model = chat_model
                updated = True
            if chat_prompt is not None:
                user.chat_system_prompt = chat_prompt
                updated = True
            if chat_temperature is not None:
                user.chat_temperature = chat_temperature
                updated = True
            if grok_model is not None:
                user.grok_model = grok_model
                updated = True
            if grok_prompt is not None:
                user.grok_system_prompt = grok_prompt
                updated = True
            if grok_temperature is not None:
                user.grok_temperature = grok_temperature
                updated = True
            if updated:
                session.commit()

        if updated:
            await interaction.response.send_message(
                "Settings updated!", ephemeral=True
            )
        else:
            embed = _build_settings_embed(user, USER_SETTINGS_FIELDS, title, discord.Color.green())
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Settings(bot))

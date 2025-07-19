import discord
import requests
from discord import app_commands
from discord.ext import commands
from client.database import Session, Servers, UserSettings
from config import BASE_SYSTEM_PROMPT

class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name='settings', invoke_without_command=True)
    @commands.is_owner()
    async def settings(self, ctx):
        if ctx.invoked_subcommand is None:
            server = Session.get(Servers, str(ctx.guild.id))
            if server:
                embed = discord.Embed(
                    title="Server Settings",
                    description=f"Use .settings model|prompt to change settings",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Model", value=f"```{server.model}```", inline=False)
                embed.add_field(name="System Prompt", value=f"```{server.system_prompt}```", inline=False)
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Server not found in database.")


    @settings.command(name='model')
    @commands.is_owner()
    async def set_model(self, ctx, *, model: str):
        if not model:
            await ctx.send("❌ Please provide a model name.")
            return
        
        # Get list of available models from OpenRouter API
        response = requests.get("https://openrouter.ai/api/v1/models")
        available_models = [model['id'] for model in response.json()["data"]]
        if model not in available_models:
            await ctx.send("❌ Invalid model name.")
        else:
            server = Session.get(Servers, str(ctx.guild.id))
            server.model = model
            Session.commit()
            await ctx.send(f"✅ Model updated successfully to {model}!")


    @settings.command(name='prompt')
    @commands.is_owner()
    async def set_prompt(self, ctx, *, prompt: str):
        if not prompt:
            await ctx.send("❌ Please provide a system prompt.")
            return
        
        server = Session.get(Servers, str(ctx.guild.id))
        server.system_prompt = prompt
        Session.commit()
        await ctx.send(f"✅ System prompt updated successfully!")

    @set_model.error
    @set_prompt.error
    async def settings_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Only bot owner can use this command.")


    @app_commands.command(name="settings", description="Show or set your personal settings")
    @app_commands.describe(model="Set your preferred model", prompt="Set your system prompt")
    @app_commands.allowed_installs(users=True, guilds=False)
    async def user_settings(self, interaction: discord.Interaction, model: str = None, prompt: str = None):
        user_id = str(interaction.user.id)
        # Fetch or create user settings
        user_settings = Session.get(UserSettings, user_id)
        if not user_settings:
            user_settings = UserSettings(id=user_id, model="google/gemini-2.0-flash-001", system_prompt=BASE_SYSTEM_PROMPT)
            Session.add(user_settings)
            Session.commit()

        # Update if provided
        updated = False
        if model:
            user_settings.model = model
            updated = True
        if prompt:
            user_settings.system_prompt = prompt
            updated = True
        if updated:
            Session.commit()
            await interaction.response.send_message("✅ Your settings have been updated!", ephemeral=True)
        else:
            embed = discord.Embed(
                title="Your Settings",
                color=discord.Color.green()
            )
            embed.add_field(name="Model", value=f"```{user_settings.model}```", inline=False)
            embed.add_field(name="System Prompt", value=f"```{user_settings.system_prompt}```", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Settings(bot))

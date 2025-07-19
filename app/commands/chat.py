import logging
import discord.ext.commands
import requests
import base64
from typing import List, Optional
from openai.types.chat import ChatCompletionMessageParam

import discord
from discord import app_commands
from discord.ext import commands
from client.openrouter import OPENROUTER_CLIENT
from client.database import Session, Servers, UserSettings
from config import BASE_SYSTEM_PROMPT, BASE_MODEL
import discord.ext

logger = logging.getLogger('discord')


class Gemini(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot 
        self.max_history_length = 20
        self.conversation_history = {}  # caching

    @staticmethod
    def roughly_calculate_tokens(text: str):
        return int(len(text) / 4)


    def image_to_base64(self, image_url: str) -> Optional[str]:
        try:
            image_bytes = requests.get(image_url).content
            return f"data:image/jpeg;base64,{base64.b64encode(image_bytes).decode('utf-8')}"
        except Exception as e:
            logger.error(f"Failed to convert image to base64: {e}")
            return None
        
    async def build_prompt(self, ctx: commands.Context, prompt: str) -> List[ChatCompletionMessageParam]:

        # If user has no conversation history, create one
        if ctx.author.id not in self.conversation_history:
            self.conversation_history[ctx.author.id] = []
        # If user is not replying to the bot, clear the conversation history
        elif ctx.message.reference and ctx.message.author != self.bot.user:
            self.conversation_history[ctx.author.id] = []

        conversation_history = self.conversation_history[ctx.author.id][-self.max_history_length:]

        # Extract image URLs from attachments
        image_urls = []
        if ctx.message.attachments:
            image_urls.extend([att.url for att in ctx.message.attachments if att.content_type.startswith('image/')])

        reply_to = ctx.message.reference and ctx.message.reference.resolved or None

        if reply_to:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            # Add images from replied message
            if replied_message.attachments:
                image_urls.extend([att.url for att in replied_message.attachments if att.content_type.startswith('image/')])
                
            if replied_message.author == self.bot.user:
                complete_prompt = conversation_history + [
                    {"role": "assistant", "content": replied_message.content},
                    {"role": "user", "content": prompt}
                ]
            else:
                self.conversation_history[ctx.author.id] = []
                complete_prompt = conversation_history + [
                    {"role": "user", "content": replied_message.content},
                    {"role": "user", "content": prompt}
                ]
        else:
            self.conversation_history[ctx.author.id] = []
            complete_prompt = [{"role": "user", "content": prompt}]

        # Add image content if present
        if image_urls:
            complete_prompt[-1]["content"] = [
                {"type": "text", "text": prompt},
                *[{"type": "image_url", "image_url": {"url": self.image_to_base64(url)}} for url in image_urls]
            ]

        self.conversation_history[ctx.author.id] = complete_prompt[-self.max_history_length:]
        return complete_prompt


    @commands.command(name="chat")
    async def chat(self, ctx: commands.Context, *, prompt: str = None):
        if not prompt:
            return
        
        async with ctx.typing():
            server = Session.get(Servers, str(ctx.guild.id))
            system_prompt = server.system_prompt or BASE_SYSTEM_PROMPT
            model = server.model or BASE_MODEL
        
            complete_prompt = [{"role": "system", "content": system_prompt}] + await self.build_prompt(ctx, prompt)
            
            # create another complete prompt but remove the type: image_url
            text_prompts = []
            for prompt in complete_prompt:
                if prompt.get('content') and isinstance(prompt['content'], list):
                    text_prompts.append(
                        {"role": prompt['role'], "content": [
                                item if item.get("type") != "image_url" else "IMAGE" for item in prompt['content']
                            ]
                        }
                    )
                else:
                    text_prompts.append(prompt)
            logger.info(text_prompts)

            response =  OPENROUTER_CLIENT.chat(
                model=model,
                messages=complete_prompt
            )

            await ctx.send(response)


    @app_commands.command(name="chat", description="Chat with the bot using your personal settings")
    @app_commands.describe(prompt="Your message to the bot")
    @app_commands.allowed_installs(users=True, guilds=False)
    async def chat_slash(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer(thinking=True)

        user_id = str(interaction.user.id)
        user_settings = Session.get(UserSettings, user_id)
        if user_settings:
            system_prompt = user_settings.system_prompt or BASE_SYSTEM_PROMPT
            model = user_settings.model or BASE_MODEL
        else:
            system_prompt = BASE_SYSTEM_PROMPT
            model = BASE_MODEL
            user = UserSettings(id=user_id, model=model, system_prompt=system_prompt)
            Session.add(user)
            Session.commit()

        context = await self.bot.get_context(interaction)
        complete_prompt = [{"role": "system", "content": system_prompt}] + await self.build_prompt(context, prompt)

        response = OPENROUTER_CLIENT.chat(
            model=model,
            messages=complete_prompt
        )

        await interaction.followup.send(response)


async def setup(bot: discord.ext.commands.Bot):
    await bot.add_cog(Gemini(bot))
    bot.tree.add_command(Gemini.chat_slash, guild=None)

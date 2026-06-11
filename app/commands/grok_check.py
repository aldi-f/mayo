import logging
import re
import requests
import base64
import discord
from discord import app_commands
from discord.ext import commands
from client.openrouter import OPENROUTER_CLIENT
from client.database import Session, UserSettings
from config import GROK_MODEL

logger = logging.getLogger('discord')

GROK_SYSTEM_PROMPT = "You are a fact-checking assistant. Your job is to verify whether the given claim is true or false using web search. Provide a clear verdict, supporting evidence, and cite your sources. Be concise but thorough."

URL_REGEX = re.compile(r'https?://[^\s<>"\'\]\)]+')


class GrokCheck(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(
            name="@grok is this true?",
            callback=self.grok_check,
            allowed_installs=discord.AppInstallationTypes(guild=True, user=True),
            allowed_contexts=discord.AppCommandContext(guild=True, dm_channel=True, private_channel=True)
        )
        self.bot.tree.add_command(self.ctx_menu)

    def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    def _extract_urls(self, *texts: str) -> list[str]:
        urls = []
        for text in texts:
            if text:
                urls.extend(URL_REGEX.findall(text))
        seen = set()
        unique = []
        for url in urls:
            url = url.rstrip('.,;:!?)]}')
            if url not in seen:
                seen.add(url)
                unique.append(url)
        return unique

    def _fetch_page_text(self, url: str, max_chars: int = 2000) -> str | None:
        try:
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                return None
            text = re.sub(r'<[^>]+>', '', resp.text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:max_chars]
        except Exception as e:
            logger.debug(f"Failed to fetch {url}: {e}")
            return None

    def _image_to_base64(self, image_url: str) -> str | None:
        try:
            image_bytes = requests.get(image_url, timeout=10).content
            return f"data:image/jpeg;base64,{base64.b64encode(image_bytes).decode('utf-8')}"
        except Exception as e:
            logger.debug(f"Failed to convert image to base64: {e}")
            return None

    async def grok_check(self, interaction: discord.Interaction, message: discord.Message):
        await interaction.response.defer(thinking=True, ephemeral=False)

        text_parts = []
        if message.clean_content:
            text_parts.append(message.clean_content)

        for embed in message.embeds:
            parts = []
            if embed.title:
                parts.append(embed.title)
            if embed.description:
                parts.append(embed.description)
            if embed.url:
                parts.append(embed.url)
            for field in embed.fields:
                if field.name:
                    parts.append(field.name)
                if field.value:
                    parts.append(field.value)
            if parts:
                text_parts.append(" | ".join(parts))

        source_text = "\n".join(text_parts)
        urls = self._extract_urls(source_text) if source_text else []

        image_attachments = [
            att for att in message.attachments
            if att.content_type and att.content_type.startswith('image/')
        ]

        other_attachments = [
            att for att in message.attachments
            if att.content_type and not att.content_type.startswith('video/') and not att.content_type.startswith('image/')
        ]

        if not source_text and not image_attachments and not other_attachments and not urls:
            await interaction.followup.send("Nothing to check in that message.", ephemeral=True)
            return

        context_parts = []
        if source_text:
            context_parts.append(f"Message content:\n{source_text}")

        for url in urls[:3]:
            page_text = self._fetch_page_text(url)
            if page_text:
                context_parts.append(f"Content from {url}:\n{page_text}")

        for att in other_attachments:
            context_parts.append(f"Attachment: {att.filename} ({att.url})")

        context_str = "\n\n".join(context_parts) if context_parts else "Verify the content of this message."

        if image_attachments:
            content_parts = [{"type": "text", "text": context_str}]
            for att in image_attachments[:4]:
                b64 = self._image_to_base64(att.url)
                if b64:
                    content_parts.append({"type": "image_url", "image_url": {"url": b64}})
            user_content = content_parts
        else:
            user_content = context_str

        user_id = str(interaction.user.id)
        user_settings = Session.get(UserSettings, user_id)
        grok_model = user_settings.grok_model if user_settings else GROK_MODEL

        messages = [
            {"role": "system", "content": GROK_SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]

        try:
            response = OPENROUTER_CLIENT.chat(
                model=grok_model,
                messages=messages,
                max_completion_tokens=1000,
                tools=[{"type": "openrouter:web_search"}]
            )
            response = URL_REGEX.sub(r'<\g<0>>', response)
            await interaction.edit_original_response(content=response)
        except Exception as e:
            logger.error(f"Grok check failed: {e}")
            await interaction.followup.send(f"Failed to check claim: {e}", ephemeral=True)
            return


async def setup(bot: commands.Bot):
    await bot.add_cog(GrokCheck(bot))
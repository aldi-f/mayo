import logging
import re
import aiohttp
import base64
import discord
from discord import app_commands
from discord.ext import commands
from client.openrouter import OPENROUTER_CLIENT
from client.database import Session, UserSettings, get_or_create_user
from config import settings

logger = logging.getLogger('discord')

URL_REGEX = re.compile(r'https?://[^\s<>"\'\]\)]+')


class GrokCheck(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(
            name="@grok is this true?",
            callback=self.grok_check,
            allowed_installs=app_commands.AppInstallationType(guild=False, user=True),
            allowed_contexts=app_commands.AppCommandContext(guild=True, dm_channel=True, private_channel=True)
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
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

    async def _fetch_page_text(self, url: str, max_chars: int = 2000) -> str | None:
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                    if resp.status != 200:
                        return None
                    html = await resp.text()
            text = re.sub(r'<[^>]+>', '', html)
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:max_chars]
        except Exception as e:
            logger.debug(f"Failed to fetch {url}: {e}")
            return None

    async def _image_to_base64(self, image_url: str) -> str | None:
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(image_url) as resp:
                    image_bytes = await resp.read()
            return f"data:image/jpeg;base64,{base64.b64encode(image_bytes).decode('utf-8')}"
        except Exception as e:
            logger.debug(f"Failed to convert image to base64: {e}")
            return None

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 1900) -> list[str]:
        words = text.split(' ')
        chunks, current, current_len = [], [], 0
        for word in words:
            word_len = len(word) + 1
            if current_len + word_len > chunk_size and current:
                chunks.append(' '.join(current))
                current, current_len = [word], len(word)
            else:
                current.append(word)
                current_len += word_len
        if current:
            chunks.append(' '.join(current))
        return chunks

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
            page_text = await self._fetch_page_text(url)
            if page_text:
                context_parts.append(f"Content from {url}:\n{page_text}")

        for att in other_attachments:
            context_parts.append(f"Attachment: {att.filename} ({att.url})")

        context_str = "\n\n".join(context_parts) if context_parts else "Verify the content of this message."

        if image_attachments:
            content_parts = [{"type": "text", "text": context_str}]
            for att in image_attachments[:4]:
                b64 = await self._image_to_base64(att.url)
                if b64:
                    content_parts.append({"type": "image_url", "image_url": {"url": b64}})
            user_content = content_parts
        else:
            user_content = context_str

        user_id = str(interaction.user.id)
        get_or_create_user(user_id)
        with Session() as session:
            user_settings = session.get(UserSettings, user_id)
        grok_model = user_settings.grok_model or settings.GROK_MODEL
        grok_prompt = user_settings.grok_system_prompt or settings.BASE_GROK_SYSTEM_PROMPT
        grok_temperature = user_settings.grok_temperature or 1.0

        messages = [
            {"role": "system", "content": grok_prompt},
            {"role": "user", "content": user_content}
        ]

        try:
            resp = await OPENROUTER_CLIENT.achat(
                model=grok_model,
                messages=messages,
                max_completion_tokens=1000,
                temperature=grok_temperature,
                tools=[
                    {"type": "openrouter:web_search"},
                    {"type": "openrouter:web_fetch"}
                ]
            )
            content = resp.choices[0].message.content[:2000]
            cost = resp.usage.cost if resp.usage and resp.usage.cost is not None else 0.0
            with Session() as session:
                user = session.get(UserSettings, user_id)
                user.grok_total_cost = (user.grok_total_cost or 0.0) + cost
                session.commit()
            response = URL_REGEX.sub(r'<\g<0>>', content)
            chunks = self._chunk_text(response)
            await interaction.edit_original_response(content=chunks[0])
            for chunk in chunks[1:]:
                await interaction.followup.send(chunk)
        except Exception as e:
            logger.error(f"Grok check failed: {e}")
            await interaction.followup.send(f"Failed to check claim: {e}", ephemeral=True)
            return


async def setup(bot: commands.Bot):
    await bot.add_cog(GrokCheck(bot))

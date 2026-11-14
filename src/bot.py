"""Discord I/O. Run from the project root with python -m src.bot."""

import io
import logging
import os
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from src.llm.ollama_client import OllamaClient, OllamaError

log = logging.getLogger(__name__)


class YoYoBot(commands.Bot):
    def __init__(self, guild_id: int | None, base_url: str, model: str) -> None:
        super().__init__(
            command_prefix="!",
            intents=discord.Intents.default(),
            allowed_mentions=discord.AllowedMentions.none(),
        )
        self.guild_id = guild_id
        self.ollama = OllamaClient(base_url, model)
        self.tree.add_command(app_commands.Command(
            name="ask", description="Ask YoYo a question using local Hermes 3.",
            callback=self.ask,
        ))

    async def setup_hook(self) -> None:
        if self.guild_id:
            guild = discord.Object(id=self.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def close(self) -> None:
        try:
            await self.ollama.close()
        finally:
            await super().close()

    @app_commands.describe(prompt="What would you like to ask?")
    async def ask(self, interaction: discord.Interaction, prompt: str) -> None:
        if not prompt.strip() or len(prompt) > 4000:
            await interaction.response.send_message(
                "Please enter a question between 1 and 4,000 characters.", ephemeral=True
            )
            return
        await interaction.response.defer(thinking=True)
        try:
            answer = await self.ollama.ask(prompt)
        except OllamaError as exc:
            await interaction.followup.send(str(exc))
            return
        except Exception:
            log.exception("Unexpected /ask failure")
            await interaction.followup.send("Something went wrong while generating the answer. Check the bot logs.")
            return
        # UTF-16 length also accounts for emoji in Discord's content limit.
        if len(answer.encode("utf-16-le")) // 2 <= 2000:
            await interaction.followup.send(answer, allowed_mentions=discord.AllowedMentions.none())
        else:
            await interaction.followup.send(
                "YoYo's answer is attached.",
                file=discord.File(io.BytesIO(answer.encode("utf-8")), filename="yoyo-answer.txt"),
            )


def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise SystemExit("Set DISCORD_TOKEN in .env before starting YoYo.")
    guild = os.getenv("DISCORD_GUILD_ID", "").strip()
    if guild and (not guild.isdigit() or int(guild) <= 0):
        raise SystemExit("DISCORD_GUILD_ID must be a positive server ID or blank.")
    bot = YoYoBot(
        int(guild) if guild else None,
        os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        os.getenv("OLLAMA_MODEL", "hermes3:8b"),
    )
    bot.run(token)


if __name__ == "__main__":
    main()

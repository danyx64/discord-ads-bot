import asyncio
import json
import logging
import os
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
CONFIG_PATH = DATA_DIR / "config.json"
MESSAGE_PATH = DATA_DIR / "message.txt"

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("discord-ads-bot")

TOKEN = os.getenv("DISCORD_TOKEN")
APPLICATION_ID = os.getenv("DISCORD_APPLICATION_ID", "").strip()
DEV_GUILD_ID = os.getenv("DEV_GUILD_ID", "").strip()

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN non impostato")


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        config = json.load(f)

    ads_count = max(1, int(config.get("ads_count", 5)))
    max_ads_count = max(1, int(config.get("max_ads_count", 10)))
    delay_seconds = max(0.0, float(config.get("delay_seconds", 1.0)))

    return {
        "ads_count": min(ads_count, max_ads_count),
        "max_ads_count": max_ads_count,
        "delay_seconds": delay_seconds,
    }


def load_message() -> str:
    text = MESSAGE_PATH.read_text(encoding="utf-8").strip()
    if not text:
        raise RuntimeError("message.txt è vuoto")
    if len(text) > 2000:
        raise RuntimeError("message.txt supera i 2000 caratteri")
    return text


intents = discord.Intents.default()
bot_kwargs = {"command_prefix": "!", "intents": intents}
if APPLICATION_ID:
    bot_kwargs["application_id"] = int(APPLICATION_ID)

bot = commands.Bot(**bot_kwargs)


def can_send_as_guild_bot(interaction: discord.Interaction) -> bool:
    """Return True when the bot is a real guild member and can post separately.

    In this mode the slash-command acknowledgement can stay ephemeral, while the
    actual configured text is sent as a normal bot message. That avoids exposing
    the command invocation publicly.
    """
    guild = interaction.guild
    channel = interaction.channel

    if guild is None or channel is None:
        return False

    me = guild.me
    if me is None:
        return False

    try:
        permissions = channel.permissions_for(me)
    except (AttributeError, TypeError):
        return False

    return permissions.view_channel and permissions.send_messages


async def send_as_guild_bot(
    interaction: discord.Interaction,
    message: str,
    count: int,
    delay_seconds: float,
) -> bool:
    """Send normal channel messages while keeping the invocation private."""
    if not can_send_as_guild_bot(interaction):
        return False

    channel = interaction.channel
    if channel is None:
        return False

    allowed_mentions = discord.AllowedMentions.none()
    sent = 0

    try:
        # Only the command user sees this acknowledgement.
        await interaction.response.defer(ephemeral=True)

        for index in range(count):
            await channel.send(message, allowed_mentions=allowed_mentions)
            sent += 1
            if index < count - 1 and delay_seconds > 0:
                await asyncio.sleep(delay_seconds)

        await interaction.followup.send(
            f"Operazione completata: {sent} messaggio/i inviato/i.",
            ephemeral=True,
        )
        return True

    except (discord.Forbidden, discord.HTTPException) as exc:
        logger.warning(
            "Invio anonimo/separato non disponibile dopo %d messaggi: %s",
            sent,
            exc,
        )

        # If nothing was posted yet, caller can safely use the interaction fallback.
        if sent == 0:
            return False

        try:
            await interaction.followup.send(
                f"Invio interrotto dopo {sent} messaggi: {exc}",
                ephemeral=True,
            )
        except discord.HTTPException:
            logger.exception("Impossibile inviare il messaggio di errore")
        return True


async def send_as_interaction(
    interaction: discord.Interaction,
    message: str,
    count: int,
    delay_seconds: float,
) -> None:
    """Fallback for User Install, DMs, and guilds where the bot is not a member."""
    allowed_mentions = discord.AllowedMentions.none()
    sent = 0

    try:
        if interaction.response.is_done():
            await interaction.followup.send(
                message,
                allowed_mentions=allowed_mentions,
            )
        else:
            await interaction.response.send_message(
                message,
                allowed_mentions=allowed_mentions,
            )
        sent = 1

        for index in range(1, count):
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)
            await interaction.followup.send(
                message,
                allowed_mentions=allowed_mentions,
            )
            sent += 1

    except discord.HTTPException as exc:
        logger.exception("Invio tramite interaction interrotto")
        try:
            await interaction.followup.send(
                f"Invio interrotto dopo {sent} messaggi: {exc}",
                ephemeral=True,
            )
        except discord.HTTPException:
            logger.exception("Impossibile inviare anche il messaggio di errore")


async def send_messages(interaction: discord.Interaction, count: int) -> None:
    try:
        message = load_message()
        config = load_config()
    except (RuntimeError, OSError, json.JSONDecodeError, ValueError) as exc:
        if interaction.response.is_done():
            await interaction.followup.send(
                f"Errore configurazione: {exc}",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"Errore configurazione: {exc}",
                ephemeral=True,
            )
        return

    # Preferred path in guilds: private acknowledgement + independent bot post.
    # This means other users only see the bot's configured message, not who ran
    # the slash command.
    handled = await send_as_guild_bot(
        interaction,
        message,
        count,
        config["delay_seconds"],
    )
    if handled:
        return

    # User-installed apps cannot arbitrarily post in guild channels where the bot
    # is not installed. In those contexts Discord requires interaction responses.
    await send_as_interaction(
        interaction,
        message,
        count,
        config["delay_seconds"],
    )


@bot.tree.command(name="ad", description="Invia una volta il testo configurato")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
async def ad(interaction: discord.Interaction) -> None:
    await send_messages(interaction, 1)


@bot.tree.command(name="ads", description="Invia più volte il testo configurato")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
async def ads(interaction: discord.Interaction) -> None:
    try:
        config = load_config()
    except (RuntimeError, OSError, json.JSONDecodeError, ValueError) as exc:
        await interaction.response.send_message(
            f"Errore configurazione: {exc}",
            ephemeral=True,
        )
        return

    await send_messages(interaction, config["ads_count"])


@bot.event
async def on_ready() -> None:
    logger.info("Connesso come %s", bot.user)

    try:
        if DEV_GUILD_ID:
            guild = discord.Object(id=int(DEV_GUILD_ID))
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            logger.info("Sincronizzati %d comandi nel server DEV", len(synced))
        else:
            synced = await bot.tree.sync()
            logger.info("Sincronizzati %d comandi globali", len(synced))
    except Exception:
        logger.exception("Errore durante la sincronizzazione degli slash command")


bot.run(TOKEN, log_handler=None)

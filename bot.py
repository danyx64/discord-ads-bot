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

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper(), format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
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
    return {"ads_count": min(ads_count, max_ads_count), "max_ads_count": max_ads_count, "delay_seconds": delay_seconds}

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

async def send_text(interaction: discord.Interaction, count: int) -> None:
    try:
        message = load_message()
        config = load_config()
    except (RuntimeError, OSError, json.JSONDecodeError, ValueError) as exc:
        await interaction.response.send_message(f"Errore configurazione: {exc}", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    sent = 0
    try:
        for index in range(count):
            if interaction.channel is None:
                raise RuntimeError("Canale non disponibile per questo comando")
            await interaction.channel.send(message, allowed_mentions=discord.AllowedMentions.none())
            sent += 1
            if index < count - 1 and config["delay_seconds"] > 0:
                await asyncio.sleep(config["delay_seconds"])
    except (discord.Forbidden, discord.HTTPException, RuntimeError) as exc:
        logger.exception("Invio interrotto")
        await interaction.followup.send(f"Invio interrotto dopo {sent} messaggi: {exc}", ephemeral=True)
        return
    await interaction.followup.send(f"Operazione completata: {sent} messaggio/i inviato/i.", ephemeral=True)

@bot.tree.command(name="ad", description="Invia una volta il testo configurato")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def ad(interaction: discord.Interaction) -> None:
    await send_text(interaction, 1)

@bot.tree.command(name="ads", description="Invia più volte il testo configurato")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def ads(interaction: discord.Interaction) -> None:
    try:
        config = load_config()
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        await interaction.response.send_message(f"Errore configurazione: {exc}", ephemeral=True)
        return
    await send_text(interaction, config["ads_count"])

@bot.event
async def on_ready() -> None:
    logger.info("Connesso come %s", bot.user)
    try:
        if DEV_GUILD_ID:
            guild = discord.Object(id=int(DEV_GUILD_ID))
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
        else:
            synced = await bot.tree.sync()
        logger.info("Sincronizzati %d comandi", len(synced))
    except Exception:
        logger.exception("Errore durante la sincronizzazione degli slash command")

bot.run(TOKEN, log_handler=None)

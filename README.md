# Discord Ads Bot for ZimaOS

Dockerized Discord bot designed for ZimaOS.

## Commands

- `/ad` sends `message.txt` once.
- `/ads` sends it multiple times according to `config.json`.
- Automatic mentions are disabled.

## ZimaOS persistent data

The container stores configuration in `/DATA/AppData/discord-ads-bot` on the host. On first start it creates `config.json` and `message.txt` automatically.

## Required environment variables

- `DISCORD_TOKEN`: Discord bot token.
- `DISCORD_APPLICATION_ID`: Discord Application ID.
- `DEV_GUILD_ID`: optional test server ID. Leave empty for global commands.
- `LOG_LEVEL`: optional, defaults to `INFO`.

Never commit real credentials.

## Docker image

GitHub Actions publishes multi-architecture images for amd64 and arm64 to:

`ghcr.io/danyx64/discord-ads-bot:latest`

For anonymous pulls from ZimaOS, set the GHCR package visibility to Public.

## ZimaOS

Import `docker-compose.yml` using the custom app / Docker Compose installer, enter the Discord environment values, then deploy.

## Discord Developer Portal

Enable Guild Install. Enable User Install if you want user-installed application commands. For Guild Install use `bot` and `applications.commands` scopes and grant View Channels and Send Messages. Privileged Gateway Intents are not required by this bot.

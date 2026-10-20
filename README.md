# Bot1cs Status Bot

Telegram bot for checking a CS 1.6 server with the `/mix` command.

## Render deployment

This version is prepared to run as a Render Web Service.

### Environment variables

Required:

- `BOT_TOKEN` — Telegram bot token from BotFather.

Optional:

- `SERVER_IP` — defaults to `91.211.118.97`
- `SERVER_PORT` — defaults to `27027`
- `A2S_TIMEOUT` — defaults to `5.0`

`PORT` is supplied automatically by Render.

### Deploy

1. Push these files to a GitHub repository.
2. In Render, create a new Web Service from the repository, or use `render.yaml`.
3. Add `BOT_TOKEN` as a secret Environment Variable.
4. Deploy.
5. Open Telegram and test `/start` and `/mix`.

The app exposes `/health` so Render can verify that the service is alive.

## Security

Never commit the Telegram token to GitHub. If a token was previously stored directly in `bot.py`, revoke it in BotFather and generate a new one before deploying.

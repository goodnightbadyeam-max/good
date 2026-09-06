# LoIzDealsbot

Updated Telegram bot + Mini App + reviews site.

## Runtime
- Python + aiogram + Flask
- Render Web Service entrypoint: `python start_simple.py`
- `WEBAPP_URL` is taken from Render's `RENDER_EXTERNAL_URL` automatically.
- `BOT_TOKEN` is required as a Render environment variable.

## Important
The bot stores users/deals/settings in JSON files. Render Free has an ephemeral filesystem, so production persistence requires a database or paid persistent disk.

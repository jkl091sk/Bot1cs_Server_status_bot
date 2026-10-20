import asyncio
import html
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import a2s
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
SERVER_IP = os.getenv("SERVER_IP", "91.211.118.97").strip()
SERVER_PORT = int(os.getenv("SERVER_PORT", "27027"))
A2S_TIMEOUT = float(os.getenv("A2S_TIMEOUT", "5.0"))
PORT = int(os.getenv("PORT", "10000"))


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logger = logging.getLogger("bot1cs-status")


# ============================================================
# RENDER HEALTH SERVER
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/health", "/healthz"):
            body = b"Bot1cs Status Bot is running"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        return


def start_health_server():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), HealthHandler)
    logger.info("Health server listening on port %s", PORT)
    server.serve_forever()


# ============================================================
# HELPERS
# ============================================================

def safe_text(value):
    if value is None:
        return ""
    return html.escape(str(value))


def format_time(seconds):
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return "0м"

    seconds = max(seconds, 0)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours > 0:
        return f"{hours}ч {minutes}м"
    if minutes > 0:
        return f"{minutes}м"
    return f"{seconds}с"


# ============================================================
# CS 1.6 A2S
# ============================================================

def get_server_data():
    address = (SERVER_IP, SERVER_PORT)

    try:
        info = a2s.info(address, timeout=A2S_TIMEOUT)
    except Exception as error:
        logger.warning("Server info request failed: %s", error)
        return None

    try:
        players = a2s.players(address, timeout=A2S_TIMEOUT)
    except Exception as error:
        logger.warning("Players request failed: %s", error)
        players = []

    return {"info": info, "players": players}


def create_message(data):
    info = data["info"]
    players = data["players"]

    server_name = safe_text(getattr(info, "server_name", "CS 1.6 Server"))
    map_name = safe_text(getattr(info, "map_name", "Неизвестно"))
    player_count = getattr(info, "player_count", 0)
    max_players = getattr(info, "max_players", 0)

    player_lines = []

    if players:
        try:
            players_sorted = sorted(
                players,
                key=lambda player: getattr(player, "score", 0),
                reverse=True,
            )
        except Exception:
            players_sorted = players

        for index, player in enumerate(players_sorted, start=1):
            name = safe_text(getattr(player, "name", "Unknown")) or "Unknown"
            score = getattr(player, "score", 0)
            duration = getattr(player, "duration", 0)

            player_lines.append(
                f"{index}. <b>{name}</b> — {score} очк. ({format_time(duration)})"
            )
    else:
        player_lines.append("На сервере нет игроков.")

    players_text = "\n".join(player_lines)

    return (
        "🎮 <b>CS 1.6 SERVER STATUS</b>\n\n"
        f"🖥 <b>Сервер:</b>\n{server_name}\n\n"
        f"🌐 <b>IP:</b> <code>{safe_text(SERVER_IP)}:{SERVER_PORT}</code>\n"
        f"🗺 <b>Карта:</b> {map_name}\n"
        f"👥 <b>Игроки:</b> {player_count}/{max_players}\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🎯 <b>Игра:</b> CS 1.6\n\n"
        "👤 <b>Игроки онлайн:</b>\n"
        f"{players_text}\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🟢 <b>Сервер доступен</b>"
    )


# ============================================================
# TELEGRAM COMMANDS
# ============================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return

    message = (
        "👋 <b>Привет!</b>\n\n"
        "Я бот для проверки CS 1.6 сервера.\n\n"
        "🎮 <b>Доступные команды:</b>\n\n"
        "/mix — проверить сервер\n"
        "/help — помощь\n\n"
        f"🌐 Сервер:\n<code>{safe_text(SERVER_IP)}:{SERVER_PORT}</code>"
    )

    await update.message.reply_text(message, parse_mode=ParseMode.HTML)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return

    message = (
        "ℹ️ <b>Помощь</b>\n\n"
        "Используй команду:\n\n"
        "🎮 <code>/mix</code>\n\n"
        "Бот проверит CS 1.6 сервер и покажет:\n\n"
        "🟢 доступность сервера\n"
        "🗺 текущую карту\n"
        "👥 количество игроков\n"
        "👤 список игроков\n"
        "🎯 очки игроков\n"
        "⏱ время игроков на сервере\n\n"
        f"🌐 <b>Сервер:</b>\n"
        f"<code>{safe_text(SERVER_IP)}:{SERVER_PORT}</code>"
    )

    await update.message.reply_text(message, parse_mode=ParseMode.HTML)


async def mix_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return

    waiting_message = await update.message.reply_text(
        "🔄 <b>Проверяю CS 1.6 сервер...</b>",
        parse_mode=ParseMode.HTML,
    )

    try:
        data = await asyncio.to_thread(get_server_data)
    except Exception as error:
        logger.exception("Unexpected server query error: %s", error)
        data = None

    if data is None:
        message = (
            "⚠️ <b>Сервер в данный момент недоступен.</b>\n\n"
            f"🌐 <code>{safe_text(SERVER_IP)}:{SERVER_PORT}</code>\n\n"
            "Попробуйте проверить немного позже."
        )
    else:
        message = create_message(data)

    try:
        await waiting_message.edit_text(message, parse_mode=ParseMode.HTML)
    except Exception as error:
        logger.warning("Could not edit status message: %s", error)
        try:
            await update.message.reply_text(message, parse_mode=ParseMode.HTML)
        except Exception:
            logger.exception("Could not send fallback status message")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Telegram error", exc_info=context.error)


# ============================================================
# MAIN
# ============================================================

def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is missing. Add BOT_TOKEN in Render Environment Variables."
        )

    logger.info("Starting Bot1cs Status Bot")
    logger.info("CS 1.6 server: %s:%s", SERVER_IP, SERVER_PORT)

    health_thread = threading.Thread(
        target=start_health_server,
        name="health-server",
        daemon=True,
    )
    health_thread.start()

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("mix", mix_command))
    application.add_error_handler(error_handler)

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()

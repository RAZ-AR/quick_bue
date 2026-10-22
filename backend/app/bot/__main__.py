"""Telegram bot: `python -m app.bot`. For now only /start with a link to the web app.

Planned: order notifications and inline "Accept / Counter / Decline" buttons for offers.
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from app.config import get_settings

log = logging.getLogger("qb.bot")
dp = Dispatcher()

GREETING = {
    "hy": "Բարի գալուստ QB՝ ապրանքների պատվեր HoReCa-ի համար։",
    "ru": "Добро пожаловать в QB — закупки для HoReCa.",
    "en": "Welcome to QB — purchasing for HoReCa.",
}


@dp.message(CommandStart())
async def start(message: Message) -> None:
    lang = (message.from_user.language_code or "hy")[:2] if message.from_user else "hy"
    url = get_settings().web_app_url
    button = (
        InlineKeyboardButton(text="QB", web_app=WebAppInfo(url=url))
        if url.startswith("https://")
        else InlineKeyboardButton(text="QB", url=url)
    )
    await message.answer(
        GREETING.get(lang, GREETING["hy"]), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[button]])
    )


async def main() -> None:
    token = get_settings().telegram_bot_token
    if not token:
        log.warning("TELEGRAM_BOT_TOKEN is empty: bot is idle")
        await asyncio.Event().wait()
    await dp.start_polling(Bot(token))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

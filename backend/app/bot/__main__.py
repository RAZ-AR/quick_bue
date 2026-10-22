"""Telegram bot: `python -m app.bot`. /start opens the web app; /start <token> links the chat to a QB user
so that notifications arrive here (the token comes from "Link Telegram" in the web app).

Notifications themselves are sent by the scheduler through the Bot API (app/integrations/telegram_sender.py).
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from app.config import get_settings
from app.db import get_sessionmaker
from app.platform.errors import ValidationFailed
from app.services import notifications

log = logging.getLogger("qb.bot")
dp = Dispatcher()

GREETING = {
    "hy": "Բարի գալուստ QB՝ ապրանքների պատվեր HoReCa-ի համար։",
    "ru": "Добро пожаловать в QB — закупки для HoReCa.",
    "en": "Welcome to QB — purchasing for HoReCa.",
}


LINKED = {
    "hy": "Պատրաստ է․ QB-ի ծանուցումները կգան այստեղ։",
    "ru": "Готово: уведомления QB будут приходить сюда.",
    "en": "Done: QB notifications will arrive here.",
}
LINK_FAILED = {
    "hy": "Հղումը հնացել է։ Բացեք QB-ն և նորից սեղմեք «Կապել Telegram-ը»։",
    "ru": "Ссылка устарела. Откройте QB и снова нажмите «Привязать Telegram».",
    "en": "The link has expired. Open QB and press “Link Telegram” again.",
}


@dp.message(CommandStart(deep_link=True))
async def start_with_token(message: Message, command: CommandObject) -> None:
    lang = (message.from_user.language_code or "hy")[:2] if message.from_user else "hy"
    if not message.from_user or not command.args:
        return await start(message)
    async with get_sessionmaker()() as session:
        try:
            await notifications.link_telegram(session, command.args, message.from_user.id)
            await session.commit()
        except ValidationFailed:
            await message.answer(LINK_FAILED.get(lang, LINK_FAILED["ru"]))
            return None
    await message.answer(LINKED.get(lang, LINKED["ru"]))
    return None


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

"""The bell and how a person wants to be told: in-app notifications, e-mail and Telegram copies."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.auth.deps import CurrentUser, Session
from app.config import get_settings
from app.integrations import telegram_sender
from app.platform.clock import utcnow
from app.schemas import NotificationOut, NotificationPage, NotifySettings, NotifySettingsIn, ReadIn
from app.services import notifications as svc

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=NotificationPage)
async def list_notifications(user: CurrentUser, session: Session) -> NotificationPage:
    rows, unread = await svc.list_for_user(session, user)
    return NotificationPage(items=[NotificationOut.model_validate(n) for n in rows], unread=unread)


@router.post("/notifications/read", status_code=204)
async def read_notifications(body: ReadIn, user: CurrentUser, session: Session) -> None:
    await svc.mark_read(session, user, utcnow(), ids=body.ids)
    await session.commit()


def _settings_out(user) -> NotifySettings:
    return NotifySettings(
        email=user.notify_email,
        telegram=user.notify_telegram,
        email_address=user.email,
        telegram_linked=user.telegram_id is not None,
        telegram_available=telegram_sender.enabled() and bool(get_settings().telegram_bot_username),
    )


@router.get("/me/notifications", response_model=NotifySettings)
async def get_settings_(user: CurrentUser) -> NotifySettings:
    return _settings_out(user)


@router.put("/me/notifications", response_model=NotifySettings)
async def save_settings(body: NotifySettingsIn, user: CurrentUser, session: Session) -> NotifySettings:
    user.notify_email, user.notify_telegram = body.email, body.telegram
    await session.commit()
    return _settings_out(user)


class TelegramLinkOut(BaseModel):
    url: str


@router.post("/me/telegram/link", response_model=TelegramLinkOut)
async def telegram_link(user: CurrentUser) -> TelegramLinkOut:
    """A t.me link that opens the bot; its /start carries a short-lived signed token for this user."""
    bot = get_settings().telegram_bot_username.lstrip("@")
    return TelegramLinkOut(url=f"https://t.me/{bot}?start={svc.telegram_link_token(user.id)}")


@router.delete("/me/telegram", response_model=NotifySettings)
async def telegram_unlink(user: CurrentUser, session: Session) -> NotifySettings:
    user.telegram_id = None
    await session.commit()
    return _settings_out(user)

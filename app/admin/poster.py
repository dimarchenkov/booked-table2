"""Group poster utilities for admin."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.config import get_settings

settings = get_settings()

router = APIRouter()


def _resolve_bot_username() -> str | None:
    return settings.telegram_bot_username


@router.get("/admin/group-poster", response_class=HTMLResponse)
async def group_poster(request: Request) -> HTMLResponse:
    """Render a group poster page with Telegram deep link."""

    if request.session.get("token") != "admin":
        return RedirectResponse(url="/admin/login", status_code=302)

    bot_username = _resolve_bot_username()
    deep_link = f"https://t.me/{bot_username}?start=from_group" if bot_username else None
    poster_text = (
        "📦 Аренда столов для упаковки. Нажмите кнопку ниже, чтобы забронировать время."
    )

    instructions = (
        "Укажите TELEGRAM_BOT_USERNAME в .env, чтобы сформировать ссылку."
        if not bot_username
        else ""
    )

    html = f"""
    <html>
      <head><title>Group poster</title></head>
      <body style='font-family: sans-serif;'>
        <h1>Group poster</h1>
        <p>{poster_text}</p>
        <p><strong>Link:</strong> {deep_link or 'N/A'}</p>
        <p>{instructions}</p>
      </body>
    </html>
    """
    return HTMLResponse(content=html)

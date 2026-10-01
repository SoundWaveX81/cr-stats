import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class TelegramClient:
    """Client for interacting with the Telegram Bot API."""

    def __init__(self, token: str | None = None):
        self.token = token or getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send_message(
        self,
        chat_id: int | str,
        text: str,
        parse_mode: str = "HTML",
        disable_web_page_preview: bool = True,
    ) -> bool:
        """Send a formatted text message to a specific Telegram chat."""
        if not self.token:
            logger.warning("Telegram Bot Token is not configured. Message skipped.")
            return True

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, json=payload)
                if response.status_code == 200:
                    return True
                logger.error(
                    f"Failed to send Telegram message: status {response.status_code}, {response.text}"
                )
                return False
        except Exception as exc:
            logger.exception(f"Exception sending Telegram message to chat {chat_id}: {exc}")
            return False

import time

import httpx
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.bot.dispatcher import TelegramCommandDispatcher
from apps.bot.telegram_client import TelegramClient


class Command(BaseCommand):
    help = "Run the Telegram Bot locally in long-polling mode (for development and testing)."

    def handle(self, *args, **options):
        token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        if not token:
            self.stderr.write(
                self.style.ERROR(
                    "TELEGRAM_BOT_TOKEN is not configured in settings or environment variables."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS("Iniciando CR Total Telegram Bot en modo Long-Polling...")
        )
        self.stdout.write("Presiona Ctrl+C para detener el bot.")

        dispatcher = TelegramCommandDispatcher()
        client = TelegramClient(token=token)
        offset = 0

        while True:
            try:
                url = f"https://api.telegram.org/bot{token}/getUpdates"
                params = {"offset": offset, "timeout": 20}

                with httpx.Client(timeout=30.0) as http_client:
                    res = http_client.get(url, params=params)
                    if res.status_code != 200:
                        self.stderr.write(
                            self.style.WARNING(
                                f"Error al consultar getUpdates: status {res.status_code}"
                            )
                        )
                        time.sleep(3)
                        continue

                    updates = res.json().get("result", [])

                for update in updates:
                    offset = update["update_id"] + 1
                    message = update.get("message")
                    if not message or "text" not in message:
                        continue

                    chat_id = message["chat"]["id"]
                    text = message["text"]
                    user_name = message.get("from", {}).get("first_name", "Desconocido")

                    self.stdout.write(f"Mensaje de {user_name} ({chat_id}): {text}")

                    reply = dispatcher.dispatch(text)
                    if reply:
                        client.send_message(chat_id=chat_id, text=reply)

            except KeyboardInterrupt:
                self.stdout.write(self.style.SUCCESS("\nBot detenido correctamente."))
                break
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"Error en bucle de polling: {exc}"))
                time.sleep(3)

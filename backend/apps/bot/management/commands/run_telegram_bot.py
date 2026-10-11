import time

import httpx
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.bot.dispatcher import TelegramCommandDispatcher
from apps.bot.telegram_client import TelegramClient


class Command(BaseCommand):
    help = "Run the Telegram Bot locally in long-polling mode (for development and testing)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-clean-webhook",
            action="store_true",
            default=False,
            help="Do not attempt to delete active webhooks before starting long-polling.",
        )
        parser.add_argument(
            "--drop-pending-updates",
            action="store_true",
            default=False,
            help="Drop pending updates when starting long-polling.",
        )

    def handle(self, *args, **options):
        token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        if not token:
            self.stderr.write(
                self.style.ERROR(
                    "TELEGRAM_BOT_TOKEN is not configured in settings or environment variables."
                )
            )
            return

        clean_webhook = not options.get("no_clean_webhook", False)
        drop_pending = options.get("drop_pending_updates", False)

        self.stdout.write(
            self.style.SUCCESS("Iniciando CR Total Telegram Bot en modo Long-Polling...")
        )

        client = TelegramClient(token=token)

        # 1. Eliminar cualquier webhook activo en Telegram para evitar error 409 Conflict
        if clean_webhook:
            try:
                success = client.delete_webhook(drop_pending_updates=drop_pending)
                if success:
                    self.stdout.write(
                        self.style.SUCCESS(
                            "Webhook previo verificado y limpiado en Telegram para permitir Long-Polling."
                        )
                    )
            except Exception as exc:
                self.stderr.write(
                    self.style.WARNING(f"Advertencia al verificar/limpiar webhook previo: {exc}")
                )

        self.stdout.write("Presiona Ctrl+C para detener el bot.")

        dispatcher = TelegramCommandDispatcher()
        offset = 0

        with httpx.Client(timeout=35.0) as http_client:
            while True:
                try:
                    url = f"https://api.telegram.org/bot{token}/getUpdates"
                    params = {"offset": offset, "timeout": 20}

                    res = http_client.get(url, params=params)
                    if res.status_code != 200:
                        detail = ""
                        try:
                            detail = res.json().get("description", res.text)
                        except Exception:
                            detail = res.text

                        self.stderr.write(
                            self.style.WARNING(
                                f"Error al consultar getUpdates: status {res.status_code} - {detail}"
                            )
                        )

                        # Auto-recuperación si persiste conflicto por webhook activo
                        if res.status_code == 409:
                            detail_lower = detail.lower()
                            if "webhook" in detail_lower:
                                self.stdout.write(
                                    self.style.NOTICE(
                                        "Detectado conflicto 409 por webhook activo. Intentando eliminar webhook automáticamente..."
                                    )
                                )
                                client.delete_webhook(drop_pending_updates=drop_pending)
                            elif "terminated by other getupdates request" in detail_lower:
                                self.stderr.write(
                                    self.style.ERROR(
                                        "Conflicto 409: Hay otra instancia del bot ejecutándose simultáneamente con el mismo TELEGRAM_BOT_TOKEN. "
                                        "Asegúrate de que solo exista un contenedor o proceso de polling activo."
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

                        reply = dispatcher.dispatch(text, chat_id=chat_id)
                        if reply:
                            client.send_message(chat_id=chat_id, text=reply)

                except KeyboardInterrupt:
                    self.stdout.write(self.style.SUCCESS("\nBot detenido correctamente."))
                    break
                except httpx.RequestError as req_err:
                    self.stderr.write(self.style.WARNING(f"Error de red en getUpdates: {req_err}"))
                    time.sleep(3)
                except Exception as exc:
                    self.stderr.write(self.style.ERROR(f"Error en bucle de polling: {exc}"))
                    time.sleep(3)

import httpx
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.bot.telegram_client import TelegramClient


class Command(BaseCommand):
    help = "Manage Telegram Bot Webhook (check status, delete or set webhook)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--info",
            action="store_true",
            help="Show current Telegram webhook information.",
        )
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Delete any active Telegram webhook.",
        )
        parser.add_argument(
            "--drop-pending-updates",
            action="store_true",
            default=False,
            help="Drop pending updates when deleting or setting webhook.",
        )
        parser.add_argument(
            "--set",
            type=str,
            metavar="URL",
            help="Set Telegram webhook to the given HTTPS URL.",
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

        client = TelegramClient(token=token)

        if options["set"]:
            target_url = options["set"]
            secret_token = getattr(settings, "TELEGRAM_BOT_SECRET_TOKEN", "")
            payload = {
                "url": target_url,
                "drop_pending_updates": options["drop_pending_updates"],
            }
            if secret_token:
                payload["secret_token"] = secret_token

            with httpx.Client(timeout=10.0) as http_client:
                res = http_client.post(
                    f"https://api.telegram.org/bot{token}/setWebhook",
                    json=payload,
                )
                if res.status_code == 200 and res.json().get("ok"):
                    self.stdout.write(
                        self.style.SUCCESS(f"Webhook configurado exitosamente a: {target_url}")
                    )
                else:
                    self.stderr.write(
                        self.style.ERROR(
                            f"Error al configurar webhook: {res.status_code} - {res.text}"
                        )
                    )
            return

        if options["delete"]:
            ok = client.delete_webhook(drop_pending_updates=options["drop_pending_updates"])
            if ok:
                self.stdout.write(self.style.SUCCESS("Webhook eliminado correctamente."))
            else:
                self.stderr.write(self.style.ERROR("No se pudo eliminar el webhook."))
            return

        # Default action or --info: show status
        info = client.get_webhook_info()
        self.stdout.write(self.style.MIME("Estado actual del Webhook de Telegram:", "bold"))
        for k, v in info.items():
            self.stdout.write(f"  • {k}: {v}")

        if not info.get("url"):
            self.stdout.write(
                self.style.SUCCESS("\nNo hay webhook configurado (modo Long-Polling habilitado).")
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"\nHay un webhook activo hacia '{info.get('url')}'. "
                    "El modo Long-Polling (run_telegram_bot) fallará con status 409 mientras este webhook esté activo.\n"
                    "Para eliminarlo, ejecuta: python manage.py telegram_webhook --delete"
                )
            )

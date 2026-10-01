import os

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.bot.discord_bot import create_discord_bot


class Command(BaseCommand):
    help = "Run the interactive Discord Bot client."

    def add_arguments(self, parser):
        parser.add_argument(
            "--token",
            default=os.getenv("DISCORD_BOT_TOKEN", getattr(settings, "DISCORD_BOT_TOKEN", "")),
            help="Discord Bot Token",
        )

    def handle(self, *args, **options):
        token = options["token"]
        if not token:
            self.stderr.write(
                self.style.ERROR(
                    "DISCORD_BOT_TOKEN is not configured. Provide it via .env or --token."
                )
            )
            return

        self.stdout.write(self.style.SUCCESS("Iniciando CR Total Discord Bot..."))
        bot = create_discord_bot()
        try:
            bot.run(token)
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS("\nDiscord Bot detenido correctamente."))

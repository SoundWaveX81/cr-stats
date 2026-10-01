import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Initialize default administrator superuser if not already created."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default=os.getenv("DJANGO_SUPERUSER_USERNAME", "admin"),
            help="Superuser username (default: admin or env DJANGO_SUPERUSER_USERNAME)",
        )
        parser.add_argument(
            "--password",
            default=os.getenv("DJANGO_SUPERUSER_PASSWORD", "admin1234"),
            help="Superuser password (default: admin1234 or env DJANGO_SUPERUSER_PASSWORD)",
        )
        parser.add_argument(
            "--email",
            default=os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@cr-total.local"),
            help="Superuser email",
        )

    def handle(self, *args, **options):
        username = options["username"]
        password = options["password"]
        email = options["email"]

        user = User.objects.filter(username=username).first()
        if not user:
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Superusuario '{username}' creado exitosamente con contraseña predeterminada."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(f"El usuario '{username}' ya existe. No se realizaron cambios.")
            )

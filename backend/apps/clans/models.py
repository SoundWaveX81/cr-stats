from datetime import date

from django.db import models


class Clan(models.Model):
    tag = models.CharField(max_length=16, primary_key=True, help_text="Tag del clan (ej. #2PP)")
    name = models.CharField(max_length=255)
    medal_threshold = models.PositiveIntegerField(
        default=2000,
        help_text="Umbral mínimo de medallas para considerar participación exitosa",
    )
    war_day_reset_time = models.TimeField(
        default="10:00:00",
        help_text="Hora de reinicio de la jornada de guerra en horario UTC",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Clan"
        verbose_name_plural = "Clanes"
        ordering = ["name"]

    def clean(self):
        if self.tag:
            tag = self.tag.strip().upper()
            if not tag.startswith("#"):
                tag = f"#{tag}"
            self.tag = tag

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.name} ({self.tag})"


class Member(models.Model):
    ROLE_CHOICES = [
        ("leader", "Líder"),
        ("coLeader", "Colíder"),
        ("elder", "Veterano"),
        ("member", "Miembro"),
    ]

    tag = models.CharField(
        max_length=16, primary_key=True, help_text="Tag del jugador (ej. #PLAYERTAG)"
    )
    clan = models.ForeignKey(Clan, on_delete=models.CASCADE, related_name="members")
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=32, choices=ROLE_CHOICES, default="member")
    reliability_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100.00,
        help_text="Puntuación de fiabilidad histórica del jugador (0.00 a 100.00)",
    )
    trophies = models.PositiveIntegerField(
        default=0, help_text="Trofeos actuales del jugador en copas/liga"
    )
    donations = models.PositiveIntegerField(
        default=0, help_text="Cartas donadas en la semana actual"
    )
    donations_received = models.PositiveIntegerField(
        default=0, help_text="Cartas recibidas en donación en la semana actual"
    )
    last_seen = models.DateTimeField(
        null=True, blank=True, help_text="Última conexión registrada por Clash Royale"
    )
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Miembro"
        verbose_name_plural = "Miembros"
        ordering = ["name"]

    def clean(self):
        if self.tag:
            tag = self.tag.strip().upper()
            if not tag.startswith("#"):
                tag = f"#{tag}"
            self.tag = tag

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.name} ({self.tag}) - {self.get_role_display()}"


class WarPass(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="war_passes")
    reason = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Pase de Guerra"
        verbose_name_plural = "Pases de Guerra"
        ordering = ["-start_date"]

    def is_active_on(self, target_date: date) -> bool:
        """Determina si el pase de guerra cubre la fecha dada."""
        return self.start_date <= target_date <= self.end_date

    def __str__(self) -> str:
        return f"Pase para {self.member.name} ({self.start_date} a {self.end_date})"

from datetime import date, datetime, timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


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

    def get_reset_hour(self) -> int:
        if not self.war_day_reset_time:
            return 10
        if hasattr(self.war_day_reset_time, "hour"):
            return self.war_day_reset_time.hour
        return int(str(self.war_day_reset_time).split(":")[0])

    def get_current_war_date(self, now: datetime | None = None) -> date:
        if now is None:
            now = timezone.now()
        reset_hour = self.get_reset_hour()
        if now.hour < reset_hour:
            return (now - timedelta(days=1)).date()
        return now.date()

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


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ("member", "Miembro"),
        ("clan_admin", "Administrador de Clan"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    clan = models.ForeignKey(
        Clan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_profiles",
        help_text="Clan al que pertenece el usuario (obligatorio para no-superadmins)",
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="member",
        help_text="Rol dentro del clan",
    )
    player = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_profiles",
        help_text="Tag de jugador asociado en Clash Royale (opcional)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"

    def __str__(self) -> str:
        clan_name = self.clan.name if self.clan else "Sin Clan"
        return f"{self.user.username} ({self.get_role_display()} - {clan_name})"

    def save(self, *args, **kwargs):
        if self.user and not self.user.is_superuser:
            should_be_staff = self.role == "clan_admin"
            if self.user.is_staff != should_be_staff:
                self.user.is_staff = should_be_staff
                self.user.save(update_fields=["is_staff"])
        super().save(*args, **kwargs)


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ("CREATE", "Creación"),
        ("UPDATE", "Modificación"),
        ("DELETE", "Eliminación"),
        ("SYNC_CLAN", "Sincronización de Clan"),
        ("CREATE_WAR_PASS", "Creación de Pase de Guerra"),
        ("DELETE_WAR_PASS", "Eliminación de Pase de Guerra"),
        ("EXECUTE_ROSTER_ACTION", "Ejecución de Acción de Roster"),
        ("DISMISS_ROSTER_ACTION", "Descarte de Acción de Roster"),
        ("TEST_NOTIFICATION", "Prueba de Notificación"),
    ]

    SOURCE_CHOICES = [
        ("admin", "Django Admin"),
        ("api", "API REST"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    clan = models.ForeignKey(
        Clan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    source = models.CharField(max_length=16, choices=SOURCE_CHOICES, default="admin")
    model_name = models.CharField(max_length=64, blank=True)
    object_id = models.CharField(max_length=64, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Registro de Auditoría"
        verbose_name_plural = "Registros de Auditoría"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        username = self.user.username if self.user else "Sistema"
        clan_str = f" [{self.clan.name}]" if self.clan else ""
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {username}{clan_str}: {self.get_action_display()} ({self.model_name})"

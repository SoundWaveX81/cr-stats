from django.db import models


class RiverRace(models.Model):
    clan = models.ForeignKey("clans.Clan", on_delete=models.CASCADE, related_name="river_races")
    season_id = models.PositiveIntegerField(
        help_text="Identificador de la temporada de Clash Royale"
    )
    section_index = models.PositiveIntegerField(
        help_text="Índice de semana o tramo de la carrera (0-4)"
    )
    state = models.CharField(
        max_length=32, default="matched", help_text="Estado devuelto por la API"
    )
    clan_score = models.PositiveIntegerField(
        default=0, help_text="Puntos de fama o medallas acumuladas del clan"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Carrera Fluvial"
        verbose_name_plural = "Carreras Fluviales"
        constraints = [
            models.UniqueConstraint(
                fields=["clan", "season_id", "section_index"],
                name="unique_clan_season_section",
            )
        ]
        ordering = ["-season_id", "-section_index"]

    def __str__(self) -> str:
        return f"Carrera T{self.season_id}-S{self.section_index} ({self.clan.name})"


class WarDay(models.Model):
    DAY_TYPE_CHOICES = [
        ("training", "Entrenamiento"),
        ("war", "Guerra"),
    ]

    river_race = models.ForeignKey(RiverRace, on_delete=models.CASCADE, related_name="war_days")
    date = models.DateField(help_text="Fecha calendario de la jornada")
    day_index = models.PositiveSmallIntegerField(help_text="Índice dentro de la semana (0 a 6)")
    day_type = models.CharField(max_length=16, choices=DAY_TYPE_CHOICES, default="training")
    is_closed = models.BooleanField(
        default=False,
        help_text="Indica si la jornada ya fue evaluada por el motor de gobernanza",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Jornada de Guerra"
        verbose_name_plural = "Jornadas de Guerra"
        constraints = [
            models.UniqueConstraint(
                fields=["river_race", "date"],
                name="unique_race_date",
            )
        ]
        ordering = ["-date"]

    def __str__(self) -> str:
        return f"{self.get_day_type_display()} D{self.day_index} ({self.date}) - {self.river_race.clan.name}"


class WarAttackLog(models.Model):
    war_day = models.ForeignKey(WarDay, on_delete=models.CASCADE, related_name="attack_logs")
    member = models.ForeignKey("clans.Member", on_delete=models.CASCADE, related_name="attack_logs")
    attacks_used = models.PositiveSmallIntegerField(
        default=0, help_text="Ataques usados en la jornada (0-4)"
    )
    decks_used = models.PositiveSmallIntegerField(default=0)
    medals_earned = models.PositiveIntegerField(default=0)
    boat_attacks_count = models.PositiveSmallIntegerField(
        default=0,
        help_text="Ataques ilegales o dirigidos a barcos enemigos",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Registro de Ataque"
        verbose_name_plural = "Registros de Ataques"
        constraints = [
            models.UniqueConstraint(
                fields=["war_day", "member"],
                name="unique_warday_member_log",
            )
        ]
        ordering = ["-war_day__date", "-medals_earned"]

    def __str__(self) -> str:
        return f"{self.member.name}: {self.attacks_used}/4 ({self.medals_earned} medallas)"

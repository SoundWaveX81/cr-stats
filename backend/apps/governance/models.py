from django.db import models
from django.utils import timezone


class RosterAction(models.Model):
    ACTION_CHOICES = [
        ("promote_elder", "Ascenso a Veterano"),
        ("demote_member", "Degradación a Miembro"),
        ("kick", "Expulsión del Clan"),
        ("leadership_notice", "Aviso Informativo de Liderazgo"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pendiente de Ejecución"),
        ("executed", "Confirmado en el Juego"),
        ("dismissed", "Descartado por Líder"),
    ]

    clan = models.ForeignKey("clans.Clan", on_delete=models.CASCADE, related_name="roster_actions")
    member = models.ForeignKey(
        "clans.Member", on_delete=models.CASCADE, related_name="roster_actions"
    )
    war_day = models.ForeignKey(
        "wars.WarDay",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="roster_actions",
    )
    action_type = models.CharField(max_length=32, choices=ACTION_CHOICES)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending")
    reason = models.TextField(help_text="Motivo o detalle de la infracción o mérito")
    created_at = models.DateTimeField(auto_now_add=True)
    executed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Acción de Roster"
        verbose_name_plural = "Acciones de Roster"
        ordering = ["-created_at"]

    def mark_executed(self):
        """Confirma que el líder ejecutó la acción en el juego Clash Royale."""
        self.status = "executed"
        self.executed_at = timezone.now()
        self.save(update_fields=["status", "executed_at"])

    def mark_dismissed(self):
        """El líder decide perdonar o ignorar la recomendación."""
        self.status = "dismissed"
        self.save(update_fields=["status"])

    def __str__(self) -> str:
        return f"{self.get_action_type_display()} para {self.member.name} [{self.get_status_display()}]"

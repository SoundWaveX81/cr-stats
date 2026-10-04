# Clan War Management - Backend Core

Backend API and domain services for Clan War Management, built with Django 5, DRF, Celery, and PostgreSQL.

## Métricas y Reglas de Negocio

### Confiabilidad de Asistencia (`reliability_score`)
Mide el porcentaje histórico de cumplimiento de ataques en Días de Guerra concluidos (`is_closed=True`) a lo largo de las últimas 14 jornadas evaluadas:

$$\text{Confiabilidad (\%)} = \frac{\sum \min(\text{ataques\_usados}, 4)}{\text{días\_esperados} \times 4} \times 100$$

- **Jornadas cerradas exclusivamente:** Las jornadas abiertas en curso no penalizan el score histórico.
- **Pases de Guerra:** Las jornadas con licencia aprobada se excluyen del cómputo.
- **Nuevos miembros:** Solo se evalúan desde su fecha de ingreso (`joined_at`); quienes no tengan jornadas concluidas inician al 100.00%.
- **Monitoreo en Vivo (Opción B):** Para expulsiones tácticas antes del reinicio diario (10:00 UTC), el comando `/pendientes` y el dashboard ordenan por ataques faltantes hoy junto con el score histórico y etiqueta de riesgo (`🚨 Alto Riesgo`).

### Ingesta de Histórico de Carreras Fluviales (`riverracelog`)
El servicio `SyncRiverRaceService.sync_race_history(clan)` consume el endpoint `/v1/clans/{tag}/riverracelog` de Supercell para registrar las últimas 10 semanas de River Races concluidas con sus 4 días de guerra por semana y mazos usados por cada participante.

## Alertas Horarias y Canales de Notificación

### Cronograma de Alertas (Celery Beat)
- **Días:** Días de Guerra exclusivamente (Jueves a Domingo).
- **Horas UTC:** `06:00, 07:00, 08:00, 09:00` y `10:00` (cierre de jornada).
- **Sincronización:** Cada tarea corre `SyncRiverRaceService().sync(clan)` antes del reporte.
- **Clasificación en Alerta:**
  - 🚨 **Candidatos a Reemplazo:** $\text{ataques} = 0 \land \text{fiabilidad} < 50\%$.
  - ⚠️ **Sin Ataques:** $\text{ataques} = 0 \land \text{fiabilidad} \ge 50\%$.
  - ⏳ **En Progreso:** $1 \le \text{ataques} \le 3$.

### Comandos de Prueba (Management Commands)
```bash
# Ping de conectividad en canales configurados
python manage.py test_notifications [--provider telegram|discord_webhook]

# Forzar envío de alerta real con datos actuales de guerra
python manage.py test_notifications --send-pending [--clan TAG] [--provider telegram|discord_webhook]
```

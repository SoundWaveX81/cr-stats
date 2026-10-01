# Capability Map: Clan War Management (Phase 1: Backend Core)

| Module id | Responsibility | Depends on |
|---|---|---|
| `core-infra` | Estructura monorepo, `docker-compose.yml`, configuración base `uv`/`pyproject.toml`, Django 5 settings y suite de tests `pytest`. | — |
| `domain-models` | Modelos ORM relacionales (`clans`, `wars`, `governance`, `notifications`), migraciones iniciales y Django Admin con lenguaje ubicuo. | `core-infra` |
| `cr-ingestion` | `ClashRoyaleClient` (`httpx`, backoff exponencial, rate limiting) y servicios de sincronización (`SyncClanService`, `SyncRiverRaceService`). | `domain-models` |
| `governance-engine` | `GovernanceEngineService` (evaluación de ataques, faltas, ascensos a veterano, infracciones de ataque a barco, `WarPass` y `ReliabilityScore`). | `domain-models` |
| `notifications` | Patrón Adapter multi-proveedor (`Console`, `DiscordWebhook`, `Telegram`) desacoplado de eventos de dominio neutros. | `domain-models` |
| `celery-api` | Tareas asíncronas / periódicas Celery Beat y endpoints DRF con autenticación JWT (`/api/clans/`, `/api/roster-actions/`, etc.). | `cr-ingestion`, `governance-engine`, `notifications` |

**Build order:**
`core-infra` → `domain-models` → `cr-ingestion`, `governance-engine`, `notifications` → `celery-api`

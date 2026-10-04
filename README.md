# CR-Total: Sistema de Gestión y Gobernanza de Guerra de Clanes

**CR-Total** es una plataforma integral para clanes competitivos de **Clash Royale** (River Races). Monitorea en tiempo real el cumplimiento de ataques de guerra, calcula la confiabilidad histórica de los jugadores, automatiza las reglas de gobernanza (ascensos a Veterano, descensos y expulsiones) y despacha alertas a **Telegram** y **Discord** para optimizar la toma de decisiones del liderazgo antes del cierre de cada jornada.

---

## 📑 Tabla de Contenidos
1. [Arquitectura del Sistema](#-arquitectura-del-sistema)
2. [Estrategia de Notificaciones de Guerra](#-estrategia-de-notificaciones-de-guerra)
3. [Reglas Matemáticas de Clasificación y Confiabilidad](#-reglas-matemáticas-de-clasificación-y-confiabilidad)
4. [Reglas de Gobernanza (Roster Actions)](#-reglas-de-gobernanza-roster-actions)
5. [Guía de Configuración de Canales de Notificación](#-guía-de-configuración-de-canales-de-notificación)
6. [Comandos para Enviar y Forzar Pruebas](#-comandos-para-enviar-y-forzar-pruebas)
7. [Comandos de los Bots (Telegram y Discord)](#-comandos-de-los-bots-telegram-y-discord)

---

## 🏗 Arquitectura del Sistema

* **Backend:** Django 5, Django REST Framework, Celery, Celery Beat.
* **Base de Datos & Cache:** PostgreSQL 16, Redis 7.
* **Frontend:** React, TypeScript, Tailwind CSS, Vite.
* **Bots & Integraciones:** Telegram Bot API (webhook y polling), Discord Bot / Webhooks, Supercell Clash Royale API oficial.

---

## ⏰ Estrategia de Notificaciones de Guerra

El sistema ejecuta recordatorios automáticos de ataques pendientes para permitir al colíder/líder reemplazar jugadores inactivos antes de que cierre el día:

1. **Días Activos:** Exclusivamente **Días de Guerra** (Jueves a Domingo). En días de entrenamiento (Lunes a Miércoles) las alertas permanecen inactivas.
2. **Cronograma Horario (UTC):**
   * **06:00 UTC** (4 horas antes del cierre)
   * **07:00 UTC** (3 horas antes del cierre)
   * **08:00 UTC** (2 horas antes del cierre)
   * **09:00 UTC** (1 hora antes del cierre)
   * **10:00 UTC** (Cierre formal de la jornada)
3. **Sincronización en Vivo:** Cada ejecución de la tarea consulta primero la API de Clash Royale (`SyncRiverRaceService().sync(clan)`) para asegurar datos 100% frescos y evitar falsas alarmas.
4. **Política de Silencio vs Felicitación:**
   * Entre **06:00 y 09:00 UTC**: Si todos los miembros completaron sus ataques, el bot guarda **silencio total** (sin spam).
   * A las **10:00 UTC**: Si se registraron el 100% de ataques, se envía una notificación de felicitación y asistencia perfecta.

---

## 📐 Reglas Matemáticas de Clasificación y Confiabilidad

### 1. Clasificación de Miembros en la Alerta
Dentro de cada notificación, los jugadores con ataques pendientes se ordenan y clasifican en tres secciones bien diferenciadas:

| Categoría | Condición Lógica | Objetivo Táctico |
| :--- | :--- | :--- |
| 🚨 **Candidatos a Reemplazo** | `ataques == 0` y `fiabilidad < 50.0%` | Jugadores de alto riesgo de faltar hoy con mal historial. Prioridad para expulsar antes de las 10:00 UTC y meter refuerzos. |
| ⚠️ **Sin Ataques** | `ataques == 0` y `fiabilidad >= 50.0%` | Miembros habitualmente comprometidos que aún no han atacado. |
| ⏳ **En Progreso** | `1 <= ataques <= 3` | Miembros activos que ya comenzaron y les restan de 1 a 3 ataques. |

---

### 2. Fórmula de Confiabilidad Histórica (`reliability_score`)
La confiabilidad evalúa el porcentaje de asistencia en Días de Guerra concluidos:

$$\text{Confiabilidad (\%)} = \begin{cases}
100.00 & \text{si } |D| = 0 \\
\operatorname{round}\left(\frac{\sum_{d \in D} \min(\text{ataques}_d,\, 4)}{4 \times |D|} \times 100,\, 2\right) & \text{si } |D| > 0
\end{cases}$$

Donde:
* **$D$ (Días Computables):** Conjunto de jornadas de guerra concluidas (`is_closed=True`, `day_type='war'`) dentro de la ventana móvil de las últimas **14 jornadas** (~1 mes de guerras).
* **Jornada en curso:** La jornada actual abierta (`is_closed=False`) **no penaliza** la confiabilidad histórica; se monitorea en vivo de manera separada.
* **Pases de Guerra (`WarPass`):** Si el jugador tiene una licencia aprobada en una fecha, dicho día se excluye completamente tanto del numerador como del denominador.
* **Fecha de ingreso (`joined_at`):** No se evalúan días previos a la llegada del miembro al clan, salvo que ya existiera registro de ataque a su nombre.
* **Presunción de Inocencia:** Todo miembro nuevo sin jornadas concluidas inicia con **100.00%**.

---

## ⚖️ Reglas de Gobernanza (Roster Actions)

Al cerrar cada jornada de guerra (10:00 UTC), se generan recomendaciones automáticas:

1. **Ascenso a Veterano (`promote_elder`):**
   * Rol actual: `member`.
   * Cumplimiento perfecto: $16 / 16$ ataques en la River Race semanal.
   * Rendimiento competitivo: $\ge 2000$ medallas acumuladas.
   * Disciplina de guerra: Cero ataques a barco rival (`boat_attacks == 0`).
2. **Descenso a Miembro (`demote_member`):**
   * Rol actual: `elder`.
   * Incumplimiento: Menos de 4 ataques en un Día de Guerra sin `WarPass` vigente.
3. **Expulsión (`kick`):**
   * Rol actual: `member`.
   * Incumplimiento: Menos de 4 ataques en un Día de Guerra sin `WarPass` vigente.
4. **Inmunidad de Liderazgo (`leadership_notice`):**
   * `leader` y `coLeader` no son degradados ni expulsados automáticamente; se genera un aviso informativo dirigido al Líder del clan.

---

## 📡 Guía de Configuración de Canales de Notificación

### A. Telegram Bot
1. Agrega el bot de Telegram al grupo de tu clan y dale permisos de envío.
2. En el grupo, ejecuta:
   ```text
   /alertas #TAG_DE_TU_CLAN
   ```
   *(El bot responderá confirmando que el chat quedó registrado).*
3. **Vía Django Admin:**
   * Crear registro en **Canales de Notificación**.
   * Proveedor: `Telegram Bot`.
   * Configuración (JSON):
     ```json
     {
       "chat_id": "-1001234567890"
     }
     ```
     *(El `bot_token` se toma por defecto de las variables de entorno).*

---

### B. Discord Webhook
1. En el canal de Discord, ejecuta el comando si el bot tiene permisos de gestionar webhooks:
   ```text
   !alertas #TAG_DE_TU_CLAN
   ```
2. O bien, crea un webhook manualmente (Ajustes de canal > Integraciones > Webhooks > Copiar URL).
3. **Vía Django Admin:**
   * Crear registro en **Canales de Notificación**.
   * Proveedor: `Discord Webhook`.
   * Configuración (JSON):
     ```json
     {
       "webhook_url": "https://discord.com/api/webhooks/123456789/abcdefgh..."
     }
     ```

---

## 🧪 Comandos para Enviar y Forzar Pruebas

### 1. Desde Django Admin (1 solo clic)
1. Entra a [**Canales de Notificación**](http://localhost:8000/admin/notifications/notificationchannel/).
2. Marca las casillas de verificación de los canales que deseas probar (solo Telegram, solo Discord o ambos).
3. En el menú desplegable inferior de **Acción** (`Action`):
   * **`🔔 Enviar mensaje de prueba a los canales seleccionados`**: Envía un ping de conectividad para verificar tokens/webhooks.
   * **`⚠️ Forzar envío de alerta de ataques pendientes ahora`**: Sincroniza en tiempo real con Supercell y despacha la alerta real con los miembros que falten por atacar.
4. Haz clic en **Ir** (`Go`).

---

### 2. Desde la Terminal (CLI / Docker)
Puedes disparar pruebas directamente dentro del contenedor `api`:

```bash
# Probar conectividad en todos los canales activos
docker compose exec api python manage.py test_notifications

# Probar conectividad filtrando por proveedor
docker compose exec api python manage.py test_notifications --provider telegram
docker compose exec api python manage.py test_notifications --provider discord_webhook

# Forzar envío de alerta real de ataques pendientes a todos los canales
docker compose exec api python manage.py test_notifications --send-pending

# Forzar alerta real filtrando por clan y proveedor específico
docker compose exec api python manage.py test_notifications --clan #P8CCG2UJ --provider telegram --send-pending
docker compose exec api python manage.py test_notifications --clan #P8CCG2UJ --provider discord_webhook --send-pending
```

---

## 🤖 Comandos de los Bots (Telegram y Discord)

| Comando Telegram | Comando Discord | Descripción |
| :--- | :--- | :--- |
| `/estado [#tag]` | `!estado [#tag]` | Muestra el estado actual del clan y de la River Race en curso. |
| `/pendientes [#tag]` | `!pendientes [#tag]` | Lista los miembros con ataques pendientes hoy agrupados por riesgo. |
| `/alertas [#tag]` | `!alertas [#tag]` | Vincula el chat/canal actual para recibir alertas automáticas. |
| `/exentar [tag] [días]` | `!exentar [tag] [días]` | Otorga un Pase de Guerra (`WarPass`) a un jugador. |
| `/sanciones [#tag]` | `!sanciones [#tag]` | Muestra sanciones disciplinarias pendientes de aplicar en el juego. |
| `/sync [#tag]` | `!sync [#tag]` | Fuerza la sincronización inmediata con la API de Supercell. |
| `/help` | `!help` | Muestra el menú de ayuda y lista de comandos disponibles. |

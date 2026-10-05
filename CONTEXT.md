# Clan War Management

Monitorea la participación, cumplimiento de ataques y confiabilidad histórica de los miembros de múltiples Clanes en las River Races de Clash Royale para automatizar la gobernanza, ascensos, descensos y llamados de atención del clan mediante alertas en Discord/Telegram y un dashboard interactivo.

## Language

### Clan & Jerarquía

**Clan**:
Grupo persistente de hasta 50 jugadores en Clash Royale identificado por un tag único (`#CLANTAG`), con configuración propia de canales de notificación y umbrales de gobernanza.
_Avoid_: Equipo, guild, club

**Miembro (Member)**:
Jugador perteneciente al Clan, con un rol específico dentro del juego (Líder, Colíder, Veterano, Miembro).
_Avoid_: Usuario, cuenta, participante

**Veterano (Elder)**:
Rango intermedio en el Clan alcanzable mediante mérito automático por cumplimiento de ataques y umbral de medallas sin infracciones por barco.
_Avoid_: Oficial, sub-líder

**Acción de Roster (Roster Action)**:
Recomendación generada por el sistema para el liderazgo del Clan (Ascenso a Veterano, Descenso a Miembro, Expulsión o Notificación).
_Avoid_: Castigo, penalización, sanción, moderación

**Notificación de Liderazgo (Leadership Notice)**:
Reporte informativo emitido cuando un Líder o Colíder no cumple las condiciones de guerra, respetando su inmunidad ante expulsión o descenso.
_Avoid_: Advertencia de ban, strike

**Exención Temporal (War Pass)**:
Permiso transitorio otorgado a un Miembro (vía Django Admin o comando de Bot) que lo excluye de penalizaciones durante una River Race específica, restaurándose automáticamente a activo al finalizar la guerra.
_Avoid_: Vacaciones perpetuas, whitelist, inmunidad fija

### Guerra & Batallas

**River Race**:
Competencia semanal de Guerra de Clanes donde se obtienen Medallas para avanzar el barco del Clan por el río.
_Avoid_: Clan War 1, torneo, liga

**Día de Guerra (War Day)**:
Cada una de las jornadas de 24 horas (habitualmente de jueves a domingo) donde cada Miembro dispone de 4 ataques obligatorios.
_Avoid_: Día de entrenamiento, jornada, match day

**Día de Entrenamiento (Training Day)**:
Jornadas iniciales de la semana (lunes a miércoles) destinadas a ganar oro, no computables para sanciones ni expulsiones.
_Avoid_: Pre-guerra, warmup

**Ataque de Guerra (War Attack)**:
Cada una de las 4 batallas diarias permitidas a un Miembro durante un Día de Guerra utilizando mazos de guerra independientes.
_Avoid_: Golpe, turno, partida, hit

**Ataque a Barco (Boat Attack)**:
Ataque dirigido a las defensas o estructura del barco rival, explícitamente desaconsejado o prohibido por las normas del clan debido a su menor rendimiento en medallas.
_Avoid_: Ataque pirata, sabotaje

**Infracción por Barco (Boat Attack Infraction)**:
Incidencia registrada cuando un Miembro efectúa uno o más Ataques a Barco; señaliza al jugador en los reportes diarios y anula su elegibilidad de ascenso para esa River Race.
_Avoid_: Falta leve, strike de barco

**Medallas (Medals)**:
Puntos competitivos sumados al barco del Clan en función de la victoria o derrota en cada Ataque de Guerra.
_Avoid_: Fama, copas de guerra, trofeos

### Evaluación & Reglas

**Ataques Pendientes (Pending Attacks)**:
Cantidad de ataques no ejecutados por un Miembro durante el Día de Guerra en curso antes del reinicio diario.
_Avoid_: Ataques restantes, ataques perdidos

**Umbral de Medallas (Medal Threshold)**:
Cantidad mínima de Medallas acumuladas en una River Race (por defecto 2000) requerida para optar a un ascenso a Veterano.
_Avoid_: Meta de puntos, cuota

**Confiabilidad (Reliability Score)**:
Porcentaje histórico normalizado de asistencia y cumplimiento de ataques en Días de Guerra a lo largo de las últimas River Races (0.00% a 100.00%).
_Avoid_: Ranking, rating, karma, MMR

#### Fórmula de Cálculo:
$$\text{Confiabilidad (\%)} = \begin{cases}
100.00 & \text{si } \text{Ataques Esperados} = 0 \\
\frac{\text{Ataques Reales Realizados}}{\text{Ataques Esperados}} \times 100 & \text{si } \text{Ataques Esperados} > 0
\end{cases}$$

*(El resultado final se calcula y almacena redondeado a 2 decimales)*.

Donde:
- **Ataques Reales Realizados**: $\sum_{d \in \text{Días Computables}} \min(\text{ataques}_d, 4)$
- **Ataques Esperados**: $\text{Días Computables} \times 4$

#### Reglas de Negocio y Casos de Borde:
1. **Jornadas Concluidas Exclusivamente (`is_closed=True`):**
   Únicamente se evalúan jornadas de guerra que hayan finalizado formalmente. La jornada en curso (abierta) no penaliza la confiabilidad histórica, permitiendo a los miembros completar sus ataques hasta el reinicio diario (10:00 UTC).
2. **Ventana Móvil Histórica (`lookback_days = 14`):**
   La evaluación abarca hasta las últimas 14 jornadas de guerra cerradas (~3.5 semanas / casi un mes de River Races), asegurando que el puntaje refleje el compromiso reciente y no penalice indefinidamente ausencias lejanas.
3. **Pases de Guerra (`WarPass`):**
   Si el jugador cuenta con un Pase de Guerra aprobado vigente durante una jornada, ese día se omite completamente del cálculo (no suma ataques esperados ni penaliza).
4. **Fecha de Ingreso al Clan (`joined_at`):**
   Un miembro recién incorporado no es evaluado por guerras ocurridas antes de su ingreso al clan, salvo que ya existiese un registro de ataque (`WarAttackLog`) asociado a él en ese día.
5. **Presunción de Inocencia Inicial:**
   Todo jugador nuevo que aún no haya vivido ninguna jornada de guerra cerrada en el clan inicia con una confiabilidad de **100.00%**.
6. **Estrategia Operativa Intra-Jornada (Enfoque Dual):**
   - **Histórico:** `reliability_score` (refleja constancia en días cerrados).
   - **En Vivo (Hoy):** Comando `/pendientes` y Dashboard resaltan miembros con `0/4` hoy ordenados por menor fiabilidad histórica con etiqueta `🚨 Alto Riesgo`, facilitando la toma de decisiones de reemplazo antes de las 10:00 UTC.

### Notificaciones & Bot

**Canal de Notificación (Notification Channel)**:
Canal de mensajería (en Discord o Telegram) configurado para recibir alertas automatizadas de ataques pendientes y reportes diarios de roster.
_Avoid_: Chat room, canal de alertas

**Comando de Bot (Bot Command)**:
Instrucción interactiva ejecutada por líderes o miembros en Discord o Telegram (ej. `/exentar`, `/estado`, `/alertas`).
_Avoid_: Slash command exclusivo, trigger

---

## Estrategia de Alertas de Ataques Pendientes y Reglas de Clasificación

### 1. Cronograma y Disparador de Alertas
Las alertas horarias automáticas operan bajo las siguientes directrices:
- **Días Activos:** Exclusivamente **Días de Guerra** (Jueves, Viernes, Sábado y Domingo; `day_of_week='4,5,6,0'`). Los días de entrenamiento están exentos de alertas de ataques pendientes.
- **Ventana Horaria de Ejecución (UTC):**
  - `06:00 UTC`: 4 horas antes del cierre.
  - `07:00 UTC`: 3 horas antes del cierre.
  - `08:00 UTC`: 2 horas antes del cierre.
  - `09:00 UTC`: 1 hora antes del cierre.
  - `10:00 UTC`: Cierre formal de la jornada de guerra.
- **Sincronización en Vivo Obligatoria:** Inmediatamente antes de evaluar los miembros en cada ejecución programada, el servicio `SyncRiverRaceService().sync(clan)` consulta la API oficial de Supercell para garantizar datos en tiempo real y evitar falsos positivos de miembros que acaban de atacar.

### 2. Comportamiento ante Cumplimiento Total (0 Pendientes)
- **Horarios Intermedios (06:00 a 09:00 UTC):** Si todos los miembros activos completaron sus 4 ataques, el sistema opera en **modo silencio** (no emite mensajes para evitar spam).
- **Cierre de Jornada (10:00 UTC):** Si se registra un 100% de cumplimiento en los ataques, se envía un mensaje de felicitación y reconocimiento de asistencia perfecta a los canales vinculados.

### 3. Reglas de Clasificación de Miembros en la Alerta
Cada miembro activo sin `WarPass` vigente que tenga menos de 4 ataques usados en la jornada es clasificado en una de las siguientes tres categorías:

| Categoría | Condición Lógica | Racionalidad Operativa |
| :--- | :--- | :--- |
| 🚨 **Candidatos a Reemplazo / Expulsión** | `ataques_usados == 0` y `fiabilidad < 50.0%` | Miembros con alta probabilidad de inasistencia por historial deficiente. Candidatos prioritarios a ser reemplazados antes de las 10:00 UTC para dar cupo a nuevos jugadores. |
| ⚠️ **Sin Ataques** | `ataques_usados == 0` y `fiabilidad >= 50.0%` | Miembros habitualmente cumplidores que aún no han atacado hoy; recordatorio estándar sin urgencia de expulsión inmediata. |
| ⏳ **En Progreso / Incompleto** | `1 <= ataques_usados <= 3` | Miembros activos que ya comenzaron y les restan de 1 a 3 ataques por gastar. |


---

## Configuración y Pruebas de Canales de Notificación

### 1. Métodos de Vinculación de Canales
- **Telegram:**
  - Comando en el grupo: `/alertas [clan_tag]` (ej: `/alertas #P8CCG2UJ`). Registra automáticamente el `chat_id`.
  - Django Admin: Proveedor `telegram` con configuración JSON `{"chat_id": "-1001234567890"}`. El `bot_token` se hereda del entorno si no se define en el JSON.
- **Discord:**
  - Comando en el canal: `!alertas [clan_tag]` (crea el webhook automáticamente si el bot tiene permisos) o `!alertas [clan_tag] [webhook_url]`.
  - Django Admin: Proveedor `discord_webhook` con configuración JSON `{"webhook_url": "https://discord.com/api/webhooks/..."}`.
- **Consola / Logs:** Proveedor `console` con JSON `{}` para depuración en entornos locales o de testing.

### 2. Comandos para Enviar y Forzar Pruebas

#### Desde Django Admin:
En la sección **Canales de Notificación** (`/admin/notifications/notificationchannel/`):
1. Seleccionar los canales deseados mediante sus casillas de verificación.
2. Elegir en el menú de acciones:
   - **`🔔 Enviar mensaje de prueba a los canales seleccionados`**: Verifica la conectividad del webhook o bot emitiendo un mensaje de bienvenida.
   - **`⚠️ Forzar envío de alerta de ataques pendientes ahora`**: Ejecuta la sincronización en vivo y despacha el reporte real con los miembros pendientes clasificados según las fórmulas matemáticas.

#### Desde la Terminal (CLI / Docker):
```bash
# 1. Enviar mensaje de prueba a todos los canales activos
docker compose exec api python manage.py test_notifications

# 2. Probar conectividad filtrando por proveedor específico
docker compose exec api python manage.py test_notifications --provider telegram
docker compose exec api python manage.py test_notifications --provider discord_webhook

# 3. Forzar el envío de la alerta real de ataques pendientes (bypasseando restricciones de horario)
docker compose exec api python manage.py test_notifications --send-pending

# 4. Forzar alerta real para un clan y proveedor específico
docker compose exec api python manage.py test_notifications --clan #P8CCG2UJ --provider telegram --send-pending
```

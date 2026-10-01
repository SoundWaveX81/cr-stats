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
Porcentaje histórico normalizado de asistencia y cumplimiento de ataques en Días de Guerra a lo largo de las últimas River Races.
_Avoid_: Ranking, rating, karma, MMR

### Notificaciones & Bot

**Canal de Notificación (Notification Channel)**:
Canal de mensajería (en Discord o Telegram) configurado para recibir alertas automatizadas de ataques pendientes y reportes diarios de roster.
_Avoid_: Chat room, canal de alertas

**Comando de Bot (Bot Command)**:
Instrucción interactiva ejecutada por líderes o miembros en Discord o Telegram (ej. `/exentar`, `/estado`, `/vincular`).
_Avoid_: Slash command exclusivo, trigger

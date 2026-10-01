# Adaptadores de Notificación y Bot Desacoplados (Discord y Telegram)

Para soportar las alertas programadas y la interacción de líderes en Discord y Telegram sin duplicar lógica de negocio, se implementará un patrón de adaptadores de mensajería unificado. Celery emitirá eventos de dominio neutrales (recordatorios de ataques, reportes diarios de roster) que cada adaptador formateará según la plataforma (Embeds en Discord, Markdown/HTML en Telegram), mientras que los comandos interactivos delegarán la ejecución a servicios de aplicación compartidos.

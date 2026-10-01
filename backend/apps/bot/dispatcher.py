import logging

from .handlers.governance import handle_descartar, handle_ejecutar, handle_sanciones
from .handlers.help import handle_help
from .handlers.pending import handle_pending
from .handlers.status import handle_status
from .handlers.sync import handle_sync
from .handlers.war_pass import handle_exentar

logger = logging.getLogger(__name__)


class TelegramCommandDispatcher:
    """Dispatches text commands received from Telegram to specialized domain handlers."""

    COMMANDS = {
        "/start": handle_help,
        "/ayuda": handle_help,
        "/help": handle_help,
        "/sincronizar": handle_sync,
        "/sync": handle_sync,
        "/vincular": handle_sync,
        "/estado": handle_status,
        "/status": handle_status,
        "/pendientes": handle_pending,
        "/sanciones": handle_sanciones,
        "/ejecutar": handle_ejecutar,
        "/descartar": handle_descartar,
        "/exentar": handle_exentar,
    }

    def dispatch(self, raw_text: str) -> str:
        """Parse raw command text and route to the matching handler."""
        if not raw_text or not raw_text.strip():
            return ""

        parts = raw_text.strip().split()
        cmd = parts[0].lower()
        args = parts[1:]

        # Handle bot username mentions like /estado@my_cr_bot
        if "@" in cmd:
            cmd = cmd.split("@")[0]

        handler = self.COMMANDS.get(cmd)
        if not handler:
            if cmd.startswith("/"):
                return (
                    f"❓ Comando <code>{cmd}</code> no reconocido.\n"
                    "Escribe <code>/ayuda</code> para ver el listado de comandos disponibles."
                )
            return ""

        try:
            return handler(args)
        except Exception as exc:
            logger.exception(f"Error executing command '{cmd}': {exc}")
            return f"⚠️ Ocurrió un error inesperado al procesar el comando: <i>{exc}</i>"

def handle_help(_args: list[str]) -> str:
    """Return the interactive command reference manual for clan leaders and members."""
    return (
        "👑 <b>CR Total — Bot de Gobernanza de Clanes</b>\n\n"
        "Comandos disponibles para líderes y colíderes:\n\n"
        "📊 <b>Monitoreo de Guerra:</b>\n"
        "• <code>/sincronizar &lt;#tag&gt;</code> — Sincroniza o registra un clan con la API oficial.\n"
        "• <code>/estado [tag]</code> — Resumen de la River Race actual y medallas del clan.\n"
        "• <code>/pendientes [tag]</code> — Lista de miembros que faltan por atacar hoy.\n\n"
        "⚖️ <b>Gobernanza y Sanciones:</b>\n"
        "• <code>/sanciones [tag]</code> — Lista de acciones de roster pendientes generadas.\n"
        "• <code>/ejecutar &lt;id&gt;</code> — Marca una sanción como ejecutada en el juego.\n"
        "• <code>/descartar &lt;id&gt;</code> — Descarta una propuesta de sanción.\n\n"
        "🛡️ <b>Exenciones Temporales:</b>\n"
        "• <code>/exentar &lt;#tag&gt; &lt;dias&gt; &lt;motivo&gt;</code> — Otorga un Pase de Guerra.\n\n"
        "ℹ️ <i>Si omites el tag del clan, se usará el clan principal activo configurado.</i>"
    )

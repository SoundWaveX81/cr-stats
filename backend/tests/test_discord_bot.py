import pytest

from apps.bot.discord_bot import create_discord_bot


@pytest.mark.django_db
def test_discord_bot_registered_commands():
    """Verify Discord bot initializes with all expected interactive commands."""
    bot = create_discord_bot()
    command_names = {cmd.name for cmd in bot.commands}

    expected_commands = {
        "ayuda",
        "estado",
        "pendientes",
        "sanciones",
        "ejecutar",
        "descartar",
        "exentar",
        "sincronizar",
        "alertas",
    }
    assert expected_commands.issubset(command_names)

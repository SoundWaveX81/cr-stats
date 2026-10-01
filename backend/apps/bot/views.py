import json
import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .dispatcher import TelegramCommandDispatcher
from .telegram_client import TelegramClient

logger = logging.getLogger(__name__)


@csrf_exempt
def telegram_webhook_view(request):
    """Receive and process webhook events from the Telegram Bot API."""
    if request.method != "POST":
        return HttpResponse("Method Not Allowed", status=405)

    # Validate secret token if configured
    expected_secret = getattr(settings, "TELEGRAM_BOT_SECRET_TOKEN", "")
    if expected_secret:
        received_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if received_secret != expected_secret:
            logger.warning("Rejected Telegram webhook call with invalid secret token.")
            return HttpResponseForbidden("Invalid secret token")

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception as exc:
        logger.error(f"Malformed JSON in Telegram webhook: {exc}")
        return JsonResponse({"error": "Malformed JSON"}, status=400)

    message = data.get("message") or data.get("edited_message")
    if not message or "text" not in message:
        return JsonResponse({"status": "ignored", "reason": "No text message found"})

    chat_id = message.get("chat", {}).get("id")
    raw_text = message.get("text", "")

    if not chat_id or not raw_text:
        return JsonResponse({"status": "ignored", "reason": "Missing chat_id or text"})

    dispatcher = TelegramCommandDispatcher()
    reply_text = dispatcher.dispatch(raw_text)

    if reply_text:
        client = TelegramClient()
        client.send_message(chat_id=chat_id, text=reply_text)

    return JsonResponse({"status": "ok"})

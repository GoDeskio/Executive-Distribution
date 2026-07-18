import asyncio
import requests

from core.utils import logger


async def send_slack(settings: dict, text: str) -> bool:
    """Best-effort Slack message via the configured incoming webhook."""
    webhook = (settings.get("slack_webhook_url") or "").strip()
    if not webhook.startswith("http"):
        return False
    try:
        await asyncio.to_thread(lambda: requests.post(webhook, json={"text": text}, timeout=8))
        return True
    except Exception as e:
        logger.warning(f"slack send failed: {e}")
        return False

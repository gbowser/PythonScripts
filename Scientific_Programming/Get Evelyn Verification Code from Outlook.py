from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta


SENDER_EMAIL = "noreply@evelyn.com"
CODE_PATTERN = re.compile(r"\b(\d{6})\b")


def get_outlook_namespace():
    try:
        import win32com.client
    except ImportError as exc:
        raise SystemExit(
            "This script needs pywin32 installed. Run: uv add pywin32"
        ) from exc

    outlook = win32com.client.Dispatch("Outlook.Application")
    return outlook.GetNamespace("MAPI")


def extract_code_from_message(message) -> str | None:
    text_parts = []
    for attr in ("Subject", "Body", "HTMLBody"):
        try:
            value = getattr(message, attr, "")
        except Exception:
            value = ""
        if value:
            text_parts.append(str(value))

    combined_text = "\n".join(text_parts)
    match = CODE_PATTERN.search(combined_text)
    return match.group(1) if match else None


def sender_matches(message, sender_email: str) -> bool:
    candidates = []
    for attr in ("SenderEmailAddress", "SenderName"):
        try:
            value = getattr(message, attr, "")
        except Exception:
            value = ""
        if value:
            candidates.append(str(value).lower())

    return any(sender_email.lower() in candidate for candidate in candidates)


def received_recently(message, lookback_minutes: int) -> bool:
    try:
        received_time = message.ReceivedTime
    except Exception:
        return False

    cutoff = datetime.now(received_time.tzinfo) - timedelta(minutes=lookback_minutes)
    return received_time >= cutoff


def get_latest_code_from_outlook(
    sender_email: str = SENDER_EMAIL,
    lookback_minutes: int = 15,
) -> str:
    namespace = get_outlook_namespace()
    inbox = namespace.GetDefaultFolder(6)
    items = inbox.Items
    items.Sort("[ReceivedTime]", True)

    for message in items:
        if not sender_matches(message, sender_email):
            continue
        if not received_recently(message, lookback_minutes):
            continue

        code = extract_code_from_message(message)
        if code:
            return code

    raise LookupError(
        f"No recent 6-digit code found from {sender_email} in the last "
        f"{lookback_minutes} minutes."
    )


def main():
    sender_email = SENDER_EMAIL
    lookback_minutes = 15

    if len(sys.argv) >= 2:
        sender_email = sys.argv[1]
    if len(sys.argv) >= 3:
        lookback_minutes = int(sys.argv[2])

    code = get_latest_code_from_outlook(sender_email, lookback_minutes)
    print(code)


if __name__ == "__main__":
    main()

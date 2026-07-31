"""Monitor Dell Outlet for computers at an exact price and send email alerts."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import smtplib
import time
from dataclasses import asdict, dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


DEFAULT_URL = (
    "https://outlet.euro.dell.com/GDOOnline/Online/InventorySearch"
    "?brandId=2&c=uk&cs=ukdfb1&l=en&s=dfb"
    "&pFilter=eyJQcm9kdWN0QnJhbmQiOlsiMzU4MDAzIl0sIkZhbWlseU5hbWUi"
    "OlsiMzUxNSJdLCJQcm9jZXNzb3IiOlsiMzA1MDAyIl19"
)
DEFAULT_PRICE_PENCE = 302_400
DEFAULT_INTERVAL_SECONDS = 600
STATE_FILE = Path(__file__).with_name("monitor_state.json")

# Captures £3024, £ 3,024, £3024.00, and the corresponding non-breaking spaces.
POUND_PRICE_RE = re.compile(
    r"£\s*((?:\d{1,3}(?:,\d{3})+)|(?:\d+))(?:\.(\d{2}))?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Listing:
    price_pence: int
    description: str
    url: str

    @property
    def fingerprint(self) -> str:
        source = f"{self.price_pence}|{self.description}|{self.url}"
        return hashlib.sha256(source.encode("utf-8")).hexdigest()


def price_matches(text: str, target_pence: int) -> bool:
    """Return True when text contains a pound price exactly equal to the target."""
    for pounds, pennies in POUND_PRICE_RE.findall(text.replace("\xa0", " ")):
        value = int(pounds.replace(",", "")) * 100 + int(pennies or "00")
        if value == target_pence:
            return True
    return False


def build_driver() -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=en-GB")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0 Safari/537.36"
    )
    return webdriver.Chrome(options=options)


def find_listings(driver: webdriver.Chrome, url: str, target_pence: int) -> list[Listing]:
    driver.get(url)
    try:
        WebDriverWait(driver, 30).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        WebDriverWait(driver, 20).until(
            lambda d: "access denied" in d.title.lower()
            or len(d.find_element(By.TAG_NAME, "body").text.strip()) > 50
        )
    except TimeoutException:
        logging.warning("The page did not finish loading; checking available content.")

    body_text = driver.find_element(By.TAG_NAME, "body").text
    if "access denied" in body_text.lower():
        raise RuntimeError(
            "Dell denied this request. Try running without --headless or from a "
            "different network."
        )

    candidates = driver.execute_script(
        """
        const elements = [...document.querySelectorAll('body *')];
        const leaves = elements.filter(el => {
          const text = (el.innerText || '').trim();
          if (!text || !text.includes('£')) return false;
          return ![...el.children].some(c => (c.innerText || '').includes('£'));
        });
        return leaves.map(el => {
          let card = el;
          while (card.parentElement && card.parentElement !== document.body) {
            const parentText = (card.parentElement.innerText || '').trim();
            if (parentText.length > 1200) break;
            card = card.parentElement;
            if (card.querySelector('a[href]') && parentText.length >= 20) break;
          }
          const link = card.querySelector('a[href]') || el.closest('a[href]');
          return {
            priceText: (el.innerText || '').trim(),
            description: (card.innerText || el.innerText || '').trim(),
            url: link ? link.href : ''
          };
        });
        """
    )

    found: dict[str, Listing] = {}
    for item in candidates:
        price_text = str(item.get("priceText", ""))
        if not price_matches(price_text, target_pence):
            continue
        description = " ".join(str(item.get("description", "")).split())[:1000]
        listing = Listing(target_pence, description, str(item.get("url", "")) or url)
        found[listing.fingerprint] = listing

    # If Dell changes its markup, still detect the price and provide a useful alert.
    if not found and price_matches(body_text, target_pence):
        listing = Listing(target_pence, "Matching price found on Dell Outlet page", url)
        found[listing.fingerprint] = listing
    return list(found.values())


def load_active_fingerprints(path: Path) -> set[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return set(data.get("active_fingerprints", []))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return set()


def save_state(path: Path, listings: Iterable[Listing]) -> None:
    path.write_text(
        json.dumps(
            {
                "active_fingerprints": [item.fingerprint for item in listings],
                "active_listings": [asdict(item) for item in listings],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def send_email(
    listings: list[Listing],
    recipient: str,
    dry_run: bool = False,
    subject: str | None = None,
) -> None:
    # Hover defaults; environment variables can override these if needed.
    host = os.environ.get("SMTP_HOST", "mail.hover.com")
    user = os.environ.get("SMTP_USER", "gordon@bowser.net")
    password = os.environ.get("SMTP_PASSWORD")
    sender = os.environ.get("SMTP_FROM", user)
    port = int(os.environ.get("SMTP_PORT", "465"))
    use_ssl = os.environ.get("SMTP_SSL", "true").lower() in {"1", "true", "yes"}

    if not dry_run and (not all((host, sender)) or (user and not password)):
        raise RuntimeError(
            "Email is not configured. Set SMTP_PASSWORD for the Hover mailbox. "
            "SMTP_HOST, SMTP_USER, SMTP_PORT, SMTP_FROM, and SMTP_SSL are optional "
            "overrides."
        )

    msg = EmailMessage()
    pounds = listings[0].price_pence // 100
    msg["Subject"] = subject or f"Dell Outlet alert: £{pounds:,} computer found"
    msg["From"] = sender
    msg["To"] = recipient
    lines = ["A computer listed at exactly £3,024 was found:", ""]
    for listing in listings:
        lines.extend((listing.description, listing.url, ""))
    msg.set_content("\n".join(lines))

    if dry_run:
        logging.info("DRY RUN: would email %s\n%s", recipient, msg.get_content())
        return

    smtp_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
    with smtp_class(host, port, timeout=30) as smtp:
        if not use_ssl:
            smtp.starttls()
        if user:
            smtp.login(user, password or "")
        smtp.send_message(msg)


def check_once(
    url: str,
    target_pence: int,
    recipient: str,
    state_path: Path,
    dry_run: bool,
) -> int:
    driver = build_driver()
    try:
        listings = find_listings(driver, url, target_pence)
    finally:
        driver.quit()

    previous = load_active_fingerprints(state_path)
    new_listings = [item for item in listings if item.fingerprint not in previous]
    logging.info("Found %d matching listing(s), %d new.", len(listings), len(new_listings))
    if new_listings:
        send_email(new_listings, recipient, dry_run=dry_run)
    if not dry_run:
        save_state(state_path, listings)
    return len(listings)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--recipient", default="gordon@bowser.net")
    parser.add_argument("--price", type=int, default=3024, help="Exact whole-pound price")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_SECONDS)
    parser.add_argument("--once", action="store_true", help="Check once, then exit")
    parser.add_argument(
        "--test-email",
        action="store_true",
        help="Send a test email and exit without checking Dell",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not email or save state")
    parser.add_argument("--state-file", type=Path, default=STATE_FILE)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    if args.test_email:
        test_listing = Listing(
            args.price * 100,
            "This is a test from the Dell Outlet monitor. Email is configured correctly.",
            args.url,
        )
        send_email(
            [test_listing],
            args.recipient,
            dry_run=args.dry_run,
            subject="Test successful: Dell Outlet monitor",
        )
        logging.info("Test email sent successfully to %s.", args.recipient)
        return

    while True:
        try:
            check_once(
                args.url,
                args.price * 100,
                args.recipient,
                args.state_file,
                args.dry_run,
            )
        except (RuntimeError, WebDriverException, OSError, smtplib.SMTPException):
            logging.exception("Monitor check failed; it will retry at the next interval.")
        if args.once:
            break
        logging.info("Next check in %d seconds.", args.interval)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()

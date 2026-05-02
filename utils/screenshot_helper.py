import re
from datetime import datetime
from pathlib import Path

import allure
from playwright.sync_api import Page


SCREENSHOTS_DIR = Path("reports/screenshots")


def _sanitize(name: str) -> str:
    # Replaces invalid characters
    return re.sub(r"[^\w\-]", "_", name)


def take_screenshot(page: Page, name: str) -> Path:
    # Saving full page screenshot in reports/screenshots/
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{_sanitize(name)}_{timestamp}.png"
    file_path = SCREENSHOTS_DIR / filename
    screenshot_bytes = page.screenshot(full_page=True)
    file_path.write_bytes(screenshot_bytes)
    allure.attach(screenshot_bytes, name=name, attachment_type=allure.attachment_type.PNG)
    print(f"[Screenshot] Saved: {file_path}")
    return file_path
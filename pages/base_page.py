from pathlib import Path
from playwright.sync_api import Page


class BasePage:
    # Shared utilities: Navigation, Waiting, Screenshots

    def __init__(self, page: Page) -> None:
        self._page = page

    # Navigation
    def navigate(self, url: str) -> None:
        self._page.goto(url, wait_until="domcontentloaded")

    def get_current_url(self) -> str:
        return self._page.url

    # Waits
    def wait_for_selector(self, selector: str, timeout: int = 10_000) -> None:
        self._page.wait_for_selector(selector, timeout=timeout)

    def wait_for_url_contains(self, substring: str, timeout: int = 10_000) -> None:
        self._page.wait_for_url(f"**{substring}**", timeout=timeout)

    # Screenshots
    def take_screenshot(self, name: str, folder: str = "reports/screenshots") -> Path:
        path = Path(folder)
        path.mkdir(parents=True, exist_ok=True)
        file_path = path / f"{name}.png"
        self._page.screenshot(path=str(file_path), full_page=True)
        return file_path
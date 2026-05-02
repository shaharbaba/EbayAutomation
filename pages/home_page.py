from playwright.sync_api import Page
from pages.base_page import BasePage
from utils.screenshot_helper import take_screenshot
from utils.logger import log


class HomePage(BasePage):
    # Responsible for: navigating to eBay and performing a search query

    URL = "https://www.ebay.com"

    # Locators
    _SEARCH_INPUT = 'input[id="gh-ac"]'
    _SEARCH_BUTTON = 'button[type="submit"]'

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    def open(self) -> None:
        log(f"URL: {self.URL}", "Navigating to eBay")
        try:
            self.navigate(self.URL)
            self._page.wait_for_selector(self._SEARCH_INPUT, timeout=10_000)
        except Exception as e:
            take_screenshot(self._page, "home_page_load_failed")
            log(str(e), "Page Load Error")
            raise RuntimeError(f"[HomePage] Failed to load eBay home page: {e}")

    def search(self, query: str) -> None:
        log(f"Query: '{query}'", "Search Input")
        try:
            self._page.fill(self._SEARCH_INPUT, query)
            log("Clicking search button", "Button Click")
            self._page.click(self._SEARCH_BUTTON)
            self._page.wait_for_load_state("domcontentloaded")
        except Exception as e:
            take_screenshot(self._page, "home_page_search_failed")
            log(str(e), "Search Error")
            raise RuntimeError(f"[HomePage] Failed to search for '{query}': {e}")
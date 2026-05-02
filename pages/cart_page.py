from playwright.sync_api import Page
from pages.base_page import BasePage
from utils.price_parser import parse_price
from utils.screenshot_helper import take_screenshot
from utils.logger import log


class CartPage(BasePage):
    """
    Responsible for:
      - Opening the cart
      - Reading the subtotal
      - Asserting the total does not exceed the budget
    """

    CART_URL = "https://cart.ebay.com"

    # Locators
    _SUBTOTAL = '[data-test-id="SUBTOTAL"] span span span'

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    def open(self) -> None:
        log(f"URL: {self.CART_URL}", "Navigating to Cart")
        # Small delay before navigating to cart — reduces captcha risk
        self._page.wait_for_timeout(6_000)
        self.navigate(self.CART_URL)
        self._page.wait_for_load_state("domcontentloaded")

        # Detect captcha — eBay may redirect to captcha page during automation
        if "captcha" in self._page.url:
            take_screenshot(self._page, "cart_captcha_detected")
            log(f"Captcha detected at: {self._page.url}", "Captcha Error")
            raise RuntimeError(
                "[CartPage] eBay captcha detected — cannot access cart. "
            )

        self._page.wait_for_selector(self._SUBTOTAL, timeout=10_000)

    def get_total(self) -> float:
        raw = self._page.locator(self._SUBTOTAL).first.inner_text(timeout=5_000).strip()
        total = parse_price(raw)
        log(f"Raw: '{raw}'\nParsed: ${total:.2f}", "Cart Subtotal")
        return total

    def assert_total_not_exceeds(self, budget_per_item: float, items_count: int) -> None:
        self.open()
        take_screenshot(self._page, "cart_before_assertion")

        total = self.get_total()
        threshold = budget_per_item * items_count
        result = "PASS" if total <= threshold else "FAIL"

        log(
            f"Result    : {result}\n"
            f"Cart total: ${total:.2f}\n"
            f"Threshold : ${budget_per_item:.2f} × {items_count} items = ${threshold:.2f}",
            f"Assertion {result}",
        )

        if total > threshold:
            take_screenshot(self._page, "cart_assertion_failed")
            raise AssertionError(
                f"Cart total {total:.2f} exceeds budget {budget_per_item:.2f} × {items_count} = {threshold:.2f}"
            )

        print(f"[CartPage] Assertion passed: {total:.2f} <= {threshold:.2f}")
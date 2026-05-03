from playwright.sync_api import Page
from pages.base_page import BasePage
from utils.price_parser import is_under_or_equal, parse_price, convert_usd_to
from utils.screenshot_helper import take_screenshot
from utils.logger import log


class SearchResultsPage(BasePage):
    # Responsible for:
    #  - Applying a max price filter
    #  - Collecting item URLs that meet the price condition
    #  - Handling pagination

    # Locators
    _ITEM_CARDS  = '//li[contains(@class,"s-card")]'
    _ITEM_LINK   = 'a.s-card__link'
    _ITEM_PRICE  = 'span.s-card__price'
    _ITEM_TITLE  = '.s-card__title'
    _NEXT_BUTTON = '//a[@aria-label="Go to next search page"]'

    _RESULTS_CONTAINER = '.srp-river-main'
    _MAX_PRICE_INPUT   = '[aria-label^="Maximum Value in"]'
    _PRICE_SUBMIT_BTN  = '[aria-label="Submit price range"]'

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    # Price filter
    def apply_max_price_filter(self, max_price: float) -> None:
        try:
            el = self._page.wait_for_selector(self._MAX_PRICE_INPUT, timeout=5_000)

            # Derive currency from aria-label, e.g. "Maximum Value in ILS" to "ILS"
            aria_label = el.get_attribute("aria-label") or ""
            currency = aria_label.split(" in ")[-1].strip() if " in " in aria_label else "USD"

            # Convert max_price (USD) to the filter's currency when they differ
            price_to_fill = convert_usd_to(max_price, currency)

            self._page.fill(self._MAX_PRICE_INPUT, str(int(price_to_fill)))
            self._page.keyboard.press("Enter")
            self._page.wait_for_load_state("domcontentloaded")
            log("Clicking price filter submit button", "Button Click")
            self._page.click(self._PRICE_SUBMIT_BTN)
            self._page.wait_for_load_state("domcontentloaded")
            log(f"Max price: ${max_price} USD → {int(price_to_fill)} {currency}", "Price Filter Applied")
        except Exception:
            # Filter widget not available on this page — continue without it
            print("[SearchResultsPage] Price filter not found, skipping.")

    # Collecting items
    def _collect_items_on_page(self, max_price: float, needed: int) -> list[str]:
        # Scans the current page and returns URLs of items where their price <= max_price (stops once amount of items are reached)
        collected: list[str] = []
        log_lines: list[str] = []
        cards = self._page.locator(f"xpath={self._ITEM_CARDS}").all()

        print(f"[SearchResultsPage] Found {len(cards)} cards on page")

        for i, card in enumerate(cards):
            if len(collected) >= needed:
                break
            try:
                price_el = card.locator(self._ITEM_PRICE).first
                if price_el.count() == 0:
                    print(f"[Card {i}] No price element — skipping")
                    continue
                price_text = price_el.inner_text(timeout=2_000)
                parsed = parse_price(price_text)
                print(f"[Card {i}] price='{price_text}' | parsed={parsed} | max={max_price} | pass={parsed <= max_price}")

                if not is_under_or_equal(price_text, max_price):
                    continue

                link_el = card.locator(self._ITEM_LINK).first
                if link_el.count() == 0:
                    print(f"[Card {i}] No link element — skipping")
                    continue
                href = link_el.get_attribute("href", timeout=2_000)

                if href and href.startswith("http") and "/itm/" in href:
                    # Filter out placeholder/sponsored URLs with fake short item IDs
                    item_id = href.split("/itm/")[1].split("?")[0]
                    if len(item_id) >= 10:
                        try:
                            title_el = card.locator(self._ITEM_TITLE).first
                            if title_el.count() > 0:
                                title = title_el.inner_text(timeout=1_000).strip()
                            else:
                                # Fall back to the link's aria-label (eBay always sets this)
                                title = link_el.get_attribute("aria-label") or "N/A"
                        except Exception:
                            title = link_el.get_attribute("aria-label") or "N/A"
                        collected.append(href)
                        log_lines.append(f"  • {title}\n    Price : {price_text}\n    Link  : {href}")

            except Exception as e:
                log(str(e), f"Card {i} Error")
                continue

        if log_lines:
            log("\n\n".join(log_lines), f"Items Collected on Page ({len(log_lines)})")
        return collected

    def _has_next_page(self) -> bool:
        # Wait briefly for the pagination bar to finish rendering before deciding
        try:
            self._page.wait_for_selector(f"xpath={self._NEXT_BUTTON}", timeout=3_000)
            return True
        except Exception:
            return False

    def _go_to_next_page(self) -> None:
        current_url = self._page.url
        log(f"From : {current_url}\nAction: clicking Next page button", "Navigating to Next Page")
        self._page.locator(f"xpath={self._NEXT_BUTTON}").click()
        self._page.wait_for_load_state("domcontentloaded")

    # Public API
    def get_items_under_price(self, max_price: float, limit: int = 5) -> list[str]:
        """
        Collects up to `limit` item URLs with price <= max_price.
        Follows Next-page pagination until the limit is reached or no more pages exist.
        Returns however many were found (may be less than limit).
        """
        urls: list[str] = []

        while len(urls) < limit:
            # Wait for result cards to appear on the current page
            try:
                self._page.wait_for_selector(f"xpath={self._ITEM_CARDS}", timeout=10_000)
            except Exception:
                print("[SearchResultsPage] Timed out waiting for cards — stopping.")
                break

            if self._page.locator(f"xpath={self._ITEM_CARDS}").count() == 0:
                print("[SearchResultsPage] No cards found on page — stopping.")
                break

            needed = limit - len(urls)
            found_on_page = self._collect_items_on_page(max_price, needed)
            urls.extend(found_on_page)
            print(f"[SearchResultsPage] Page: {len(found_on_page)} qualifying — running total: {len(urls)}/{limit}")

            if len(urls) >= limit:
                break

            # Need more items — go to next page if one exists
            if self._has_next_page():
                self._go_to_next_page()
            else:
                print("[SearchResultsPage] No next page — stopping with what was found.")
                break

        if not urls:
            take_screenshot(self._page, "search_no_results_found")
            log(f"No items found under ${max_price}", "Collection Result")
        else:
            summary = "\n".join(f"{i + 1}. {u}" for i, u in enumerate(urls[:limit]))
            log(f"Collected {len(urls[:limit])}/{limit} items under ${max_price}:\n\n{summary}", "Collected Item URLs")
        return urls[:limit]
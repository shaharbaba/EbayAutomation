from __future__ import annotations
import random
from playwright.sync_api import Page
from pages.base_page import BasePage
from utils.screenshot_helper import take_screenshot
from utils.price_parser import parse_price
from utils.logger import log


class ItemPage(BasePage):
    """
    Responsible for:
      - Selecting random variants (size, color, quantity) when available
      - Clicking "Add to cart"
      - Taking a screenshot after adding
    """

    # Locators
    _VARIANT_BUTTONS  = 'button.listbox-button__control'
    _ADD_TO_CART_BTN  = '[id^="atcBtn_btn"], [id^="binBtn_btn"]'
    _CART_LAYER_CLOSE = '[id="miniCartLayer"] button[aria-label="Close"]'
    _PRICE            = '[data-testid="x-price-primary"] .ux-textspans'
    _TITLE            = 'h1.x-item-title__mainTitle'

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    # Variant selection
    def _select_random_variants(self) -> None:
        buttons = self._page.locator(self._VARIANT_BUTTONS).all()
        print(f"[ItemPage] Found {len(buttons)} variant buttons")

        for button in buttons:
            try:
                label = button.inner_text(timeout=1_000).strip().lower()
                if not label or "filter" in label or "rating" in label or "feedback" in label:
                    continue

                print(f"[ItemPage] Opening dropdown: '{label}'")
                button.click()
                self._page.wait_for_timeout(500)

                # Find options within the parent listbox container of THIS button
                parent = button.locator('xpath=ancestor::*[contains(@class,"listbox-button")][1]')
                options = parent.locator('.listbox__option').all()

                valid_options = [
                    opt for opt in options
                    if "listbox__option--active" not in (opt.get_attribute("class") or "")
                       and opt.get_attribute("aria-disabled") != "true"
                ]

                print(f"[ItemPage] {len(valid_options)} valid options for '{label}'")

                if valid_options:
                    chosen = random.choice(valid_options)
                    print(f"[ItemPage] Selecting: '{chosen.inner_text(timeout=500).strip()}'")
                    chosen.click()
                    self._page.wait_for_timeout(500)
                else:
                    self._page.keyboard.press("Escape")
                    print(f"[ItemPage] No valid options for '{label}'")

            except Exception as e:
                print(f"[ItemPage] Variant error: {e}")
                continue

    def get_title(self) -> str:
        try:
            return self._page.locator(self._TITLE).first.inner_text(timeout=3_000).strip()
        except Exception:
            return "Unknown"

    def get_price(self) -> float:
        try:
            price_el = self._page.locator(self._PRICE).first
            price_el.wait_for(timeout=5_000)
            return parse_price(price_el.inner_text())
        except Exception:
            log("Price element not found — item will be skipped", "Price Read Warning")
            return float("inf")

    # Add to cart
    def add_to_cart(self, item_url: str, max_price: float) -> float | None:
        try:
            log(f"URL: {item_url}", "Navigating to Item")
            self.navigate(item_url)
            self._page.wait_for_load_state("domcontentloaded")

            title = self.get_title()
            self._select_random_variants()

            price = self.get_price()
            log(f"Title : {title}\nPrice : ${price:.2f}\nURL   : {item_url}", "Item Details")

            if price > max_price:
                log(f"Skipped — price ${price:.2f} exceeds max ${max_price:.2f}\nTitle: {title}", "Item Skipped (Price)")
                take_screenshot(self._page, "item_skipped_price_exceeded")
                return None

            # Find Add to Cart button — prefer atcBtn over binBtn
            # Check text to avoid clicking "See in cart" or "Buy It Now"
            add_btn = None
            for selector in ['[id^="atcBtn_btn"]', '[id^="binBtn_btn"]']:
                candidate = self._page.locator(selector).first
                if candidate.count() > 0:
                    btn_text = candidate.inner_text(timeout=2_000).strip().lower()
                    print(f"[ItemPage] Found button '{btn_text}' with selector {selector}")
                    if "add to cart" in btn_text:
                        add_btn = candidate
                        break
                    elif "see in cart" in btn_text:
                        log(f"Item already in cart\nTitle: {title} | Price: ${price:.2f}", "Already in Cart")
                        take_screenshot(self._page, f"already_in_cart_{item_url.split('/')[-1][:40]}")
                        return price

            if add_btn is None:
                log(f"No 'Add to cart' button found\nTitle: {title}", "Item Skipped (No ATC Button)")
                take_screenshot(self._page, "add_to_cart_button_missing")
                return None

            log(f"Clicking 'Add to cart' for: {title}", "Button Click")
            add_btn.wait_for(timeout=5_000)
            add_btn.click()
            self._page.wait_for_timeout(2_000)

            # Check if eBay still asking to select variants
            try:
                body = self._page.locator('body').inner_text(timeout=2_000)
                if "please select" in body.lower():
                    log(f"Variant selection incomplete — item NOT added\nTitle: {title}", "Item Skipped (Variant Missing)")
                    take_screenshot(self._page, "add_to_cart_variants_missing")
                    return None
            except Exception:
                pass

            # Close mini-cart layer if it appeared
            try:
                close_btn = self._page.locator(self._CART_LAYER_CLOSE)
                if close_btn.count() > 0:
                    close_btn.click()
            except Exception:
                pass

            item_slug = item_url.split("/")[-1][:40]
            take_screenshot(self._page, f"added_to_cart_{item_slug}")
            log(f"Successfully added to cart\nTitle : {title}\nPrice : ${price:.2f}\nURL   : {item_url}", "Item Added to Cart")
            return price

        except Exception as e:
            log(f"URL  : {item_url}\nError: {e}", "Add to Cart Error")
            take_screenshot(self._page, "add_to_cart_error")
            return None
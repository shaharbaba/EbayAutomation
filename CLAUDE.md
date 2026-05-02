# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (Python 3.12 required)
pip install -r requirements.txt
playwright install chromium

# Run all tests
pytest

# Run a single test by name
pytest tests/test_ebay_flow.py::test_ebay_shopping_flow -v

# Run with e2e marker
pytest -m e2e

# Generate and open Allure report
allure serve reports/allure-results

# Open the HTML report (generated automatically after each run)
open reports/report.html
```

## Architecture

This is a **Playwright + pytest** end-to-end automation suite for eBay, following the **Page Object Model** pattern.

### Data flow

`conftest.py` → `tests/test_ebay_flow.py` orchestrates the full flow:
1. `HomePage` — navigates to ebay.com, submits a search query
2. `SearchResultsPage` — applies a max-price filter, paginates, collects item URLs where `price <= max_price`
3. `ItemPage` — navigates to each URL, selects random variants, validates the variant-adjusted price, clicks Add to Cart
4. `CartPage` — navigates to `cart.ebay.com`, reads the subtotal, asserts it ≤ `budget_per_item × items_count`

Test inputs live in `data/test_data.json` (`search_query`, `max_price`, `limit`, `base_url`).

### Key design decisions

**Persistent browser profile** — `conftest.py` uses `launch_persistent_context` with `.browser_profile/` to preserve cookies/session across runs. This is intentional to reduce eBay captcha frequency; do not switch to ephemeral contexts.

**Currency handling** — eBay may display prices in ILS (shekels). `utils/price_parser.py` fetches a live ILS→USD exchange rate on first use (cached for the session) and falls back to `0.27` if the API is unreachable. All price comparisons are always in USD.

**Double price guard** — Price is checked twice: once during search result collection (pre-navigation) and again on the item page after variant selection (post-navigation), because selecting a size/color can raise the price above `max_price`.

**Screenshots** — `utils/screenshot_helper.py` saves full-page PNGs to `reports/screenshots/` and attaches them to the Allure report automatically on every call to `take_screenshot(page, name)`.

### Page objects (`pages/`)

| File | Responsibility |
|------|---------------|
| `base_page.py` | `navigate()`, `wait_for_selector()`, `take_screenshot()` — inherited by all pages |
| `home_page.py` | `open()`, `search(query)` |
| `search_results_page.py` | `apply_max_price_filter()`, `get_items_under_price(max_price, limit)` with pagination |
| `item_page.py` | `add_to_cart(url, max_price, search_url)` — includes random variant selection |
| `cart_page.py` | `open()`, `get_total()`, `assert_total_not_exceeds(budget_per_item, items_count)` |

### Reports

- `reports/report.html` — self-contained pytest-html report, regenerated on each run
- `reports/allure-results/` — raw Allure data; view with `allure serve`
- `reports/screenshots/` — timestamped PNGs attached to Allure and saved locally

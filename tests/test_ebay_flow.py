import pytest
import allure
from pages.home_page import HomePage
from pages.search_results_page import SearchResultsPage
from pages.item_page import ItemPage
from pages.cart_page import CartPage


@allure.title("Ebay automation tests")
@allure.description("""
Full e2e flow:
1. Search for items under a max price
2. Add up to limit items to the cart
3. Assert cart total does not exceed budget
""")
@pytest.mark.e2e
def test_ebay_shopping_flow(page, test_data):
    query     = test_data["search_query"]
    max_price = test_data["max_price"]
    limit     = test_data["limit"]

    # Step 1: Search
    with allure.step(f"Open eBay and search for '{query}'"):
        home = HomePage(page)
        home.open()
        home.search(query)

    # Step 2: Filter and collect item URLs
    with allure.step(f"Filter results under ${max_price} and collect up to {limit} items"):
        search = SearchResultsPage(page)
        search.apply_max_price_filter(max_price)
        urls = search.get_items_under_price(max_price=max_price, limit=limit)

        if not urls:
            pytest.skip(f"No items found under ${max_price}")
        print(f"[Test] Found {len(urls)} items to process")

    # Step 3: Add items to cart
    with allure.step(f"Add items to cart (max ${max_price} each)"):
        item_page = ItemPage(page)
        added_prices = []
        search_url = page.url  # Save search URL to return to after adding items

        for url in urls:
            price = item_page.add_to_cart(url, max_price=max_price)
            if price is not None:
                added_prices.append(price)
            # Return to search results after each item per requirements
            page.goto(search_url, wait_until="domcontentloaded")

        assert added_prices, "No items were successfully added to the cart"
        print(f"[Test] Successfully added {len(added_prices)} items: {added_prices}")

    # Step 4: Assert cart total
    with allure.step(f"Verify cart total does not exceed ${max_price} × {len(added_prices)}"):
        cart = CartPage(page)
        cart.assert_total_not_exceeds(
            budget_per_item=max_price,
            items_count=len(added_prices)
        )
import re
import urllib.request
import json

# Fallback rate if live fetch fails
_FALLBACK_ILS_TO_USD = 0.27
_cached_rate: float | None = None
_cached_usd_rates: dict | None = None


def _get_ils_to_usd_rate() -> float:
    global _cached_rate
    if _cached_rate is not None:
        return _cached_rate
    try:
        url = "https://api.exchangerate-api.com/v4/latest/ILS"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
            _cached_rate = data["rates"]["USD"]
            print(f"[PriceParser] Live ILS→USD rate: {_cached_rate}")
            return _cached_rate
    except Exception:
        print(f"[PriceParser] Could not fetch rate, using fallback: {_FALLBACK_ILS_TO_USD}")
        _cached_rate = _FALLBACK_ILS_TO_USD
        return _cached_rate


def _get_usd_rates() -> dict:
    global _cached_usd_rates
    if _cached_usd_rates is not None:
        return _cached_usd_rates
    try:
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
            _cached_usd_rates = data["rates"]
            return _cached_usd_rates
    except Exception:
        print("[PriceParser] Could not fetch USD rates, conversion will be skipped")
        _cached_usd_rates = {}
        return _cached_usd_rates


def convert_usd_to(amount: float, target_currency: str) -> float:
    """Convert a USD amount to the given ISO currency code (e.g. 'ILS', 'EUR')."""
    code = target_currency.upper().strip()
    if code in ("USD", "$"):
        return amount
    rates = _get_usd_rates()
    rate = rates.get(code)
    if rate is None:
        print(f"[PriceParser] No rate found for '{code}', using original USD amount")
        return amount
    converted = round(amount * rate, 2)
    print(f"[PriceParser] Converted ${amount} USD → {converted} {code} (rate: {rate})")
    return converted


# Parses a price string into a USD float
# Handles formats like: "12.33$", "2.42", "42,020$ US"
# "33.50$ to 55$" --> returns the lower bound
# "ILS 229.33"    --> converts to USD automatically
# "Free Shipping" --> returns 0.0
def parse_price(price_text: str) -> float:
    if not price_text:
        return float("inf")

    text = price_text.strip()

    # Detect if price is in ILS (shekels)
    is_ils = "ILS" in text or "₪" in text

    # If there is a range ("$10.00 to $20.00" for example), take the first number
    text = text.split(" to ")[0]

    cleaned = re.sub(r"[^\d.]", "", text.replace(",", ""))
    try:
        amount = float(cleaned)
    except ValueError:
        return float("inf")

    # Convert ILS to USD so comparison is always in the same currency
    if is_ils:
        rate = _get_ils_to_usd_rate()
        amount = round(amount * rate, 2)

    return amount


def is_under_or_equal(price_text: str, max_price: float) -> bool:
    # Returns true if the parsed price (in USD) is <= max_price
    return parse_price(price_text) <= max_price
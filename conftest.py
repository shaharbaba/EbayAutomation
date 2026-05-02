import json
import shutil
import pytest
from pathlib import Path
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

_ROOT = Path(__file__).parent
_SCREENSHOTS_DIR  = _ROOT / "reports" / "screenshots"
_ALLURE_RESULTS_DIR = _ROOT / "reports" / "allure-results"
_KEEP_RUNS = 10


def _cleanup_reports() -> None:
    # Wipe allure-results so each run shows only its own data in the report
    if _ALLURE_RESULTS_DIR.exists():
        shutil.rmtree(_ALLURE_RESULTS_DIR)
    _ALLURE_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Keep only the last _KEEP_RUNS runs of screenshots
    # A "run" boundary is a gap of more than 30 minutes between consecutive files
    if not _SCREENSHOTS_DIR.exists():
        return
    files = sorted(_SCREENSHOTS_DIR.glob("*.png"), key=lambda f: f.stat().st_mtime)
    if not files:
        return

    runs: list[list[Path]] = []
    current: list[Path] = [files[0]]
    for f in files[1:]:
        if f.stat().st_mtime - current[-1].stat().st_mtime > 1800:  # 30-min gap = new run
            runs.append(current)
            current = [f]
        else:
            current.append(f)
    runs.append(current)

    to_delete = runs[:-_KEEP_RUNS] if len(runs) > _KEEP_RUNS else []
    deleted = sum(f.unlink() or 1 for run in to_delete for f in run)
    if deleted:
        print(f"[Cleanup] Removed {deleted} screenshots from {len(to_delete)} old run(s); kept last {min(len(runs), _KEEP_RUNS)}")


# Helpers
def load_test_data() -> dict:
    data_path = _ROOT / "data" / "test_data.json"
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


# Fixtures
@pytest.fixture(scope="session", autouse=True)
def cleanup_reports() -> None:
    # Runs once at session start: clears allure-results and prunes old screenshots
    _cleanup_reports()


@pytest.fixture(scope="session")
def test_data() -> dict:
    # Loads test data from data/test_data.json once per session
    return load_test_data()


@pytest.fixture(scope="session")
def browser_instance():
    # Launches a single browser for the entire test session
    with sync_playwright() as p:
        browser: Browser = p.chromium.launch(
            headless=False,
            slow_mo=800,
            args=["--disable-blink-features=AutomationControlled"],
        )
        yield browser
        browser.close()


@pytest.fixture(scope="session")
def context(browser_instance: Browser):
    # Single context for the entire session — preserves cookies/cart between navigations
    ctx: BrowserContext = browser_instance.new_context(
        viewport={"width": 1280, "height": 900},
        locale="en-US",
        timezone_id="America/New_York",
        geolocation={"latitude": 40.7128, "longitude": -74.0060},
        permissions=["geolocation"],
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
    )
    yield ctx
    ctx.close()


@pytest.fixture(scope="function")
def page(context: BrowserContext) -> Page:
    # Creates a new page per test
    p: Page = context.new_page()
    yield p
    p.close()


@pytest.fixture(scope="session")
def reports_dir() -> Path:
    # Ensures the reports directory exists and returns its path
    path = Path(__file__).parent / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path
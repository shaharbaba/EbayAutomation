import allure


def log(message: str, name: str) -> None:
    """Write to both console (always) and Allure report (when running with --alluredir)."""
    print(f"[{name}] {message}")
    allure.attach(message, name=name, attachment_type=allure.attachment_type.TEXT)
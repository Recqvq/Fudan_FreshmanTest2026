import json
import os
from pathlib import Path
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait

from environment import (
    browser_profile_path,
    cookie_path,
    input_wait_time,
    main_page,
    page_load_timeout,
)


def create_driver(headless=False, profile_path=browser_profile_path):
    """Create Chrome through Selenium Manager; no driver path is needed."""
    options = webdriver.ChromeOptions()
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    if profile_path:
        profile = Path(profile_path).resolve()
        profile.mkdir(parents=True, exist_ok=True)
        options.add_argument(f"--user-data-dir={profile}")
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
    browser = webdriver.Chrome(options=options)
    browser.set_page_load_timeout(page_load_timeout)
    return browser


def _is_target_quiz(current_url, target_url):
    current = urlparse(current_url)
    target = urlparse(target_url)
    return current.netloc == target.netloc and target.path in current.path


def wait_for_manual_auth(browser, target_url=main_page, timeout=input_wait_time):
    try:
        WebDriverWait(browser, timeout).until(
            lambda driver: _is_target_quiz(driver.current_url, target_url)
        )
    except TimeoutException as exc:
        raise TimeoutException(
            f"Login did not reach the target quiz within {timeout} seconds; "
            f"current URL: {browser.current_url}"
        ) from exc
    return browser


def driver_manual_auth(
    url=main_page,
    headless=False,
    timeout=input_wait_time,
    profile_path=browser_profile_path,
):
    browser = create_driver(headless=headless, profile_path=profile_path)
    browser.get(url)
    return wait_for_manual_auth(browser, url, timeout)


def load_cookies(log_url, browser, path=cookie_path):
    """Explicitly save cookies; this is not called by the default workflow."""
    browser.get(log_url)
    input("Complete login in Chrome, then press Enter here to save cookies...")
    Path(path).write_text(
        json.dumps(browser.get_cookies(), ensure_ascii=False), encoding="utf-8"
    )


def get_cookies(browser, path=cookie_path):
    cookies = json.loads(Path(path).read_text(encoding="utf-8"))
    for cookie in cookies:
        if cookie.get("sameSite") not in {None, "Strict", "Lax", "None"}:
            cookie.pop("sameSite", None)
        browser.add_cookie(cookie)


def driver_get_with_cookies(url=main_page, path=cookie_path, headless=False):
    if not os.path.exists(path):
        return driver_manual_auth(url, headless=headless)
    browser = create_driver(headless=headless, profile_path=browser_profile_path)
    origin = urlparse(url)
    browser.get(f"{origin.scheme}://{origin.netloc}/")
    get_cookies(browser, path)
    browser.get(url)
    return wait_for_manual_auth(browser, url, timeout=30)

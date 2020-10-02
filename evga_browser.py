from datetime import datetime
from enum import Enum, auto
from queue import Queue
from time import sleep
from threading import Thread
import json
import logging
import platform
import requests
import traceback

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.remote_connection import LOGGER

from utils import get_file_path, get_geckodriver_path
from proxy_queue import ProxyQueue
import evga_config as cfg
import strings

# Nice to have: multiline progress status for each instace
# Check out usage here: https://stackoverflow.com/a/23121189

LOGGER.setLevel(logging.WARNING)
debug = False

crash_indicators = [
    'error while requesting your page',
    'internet connection problem to our website.',
    'email our web team',
    'Request Blocked',
    'Proxy',
    'proxy',
    'error occurred',
]

class BrowserStatus(Enum):
    IN_STOCK = auto()
    LOGOUT = auto()
    KILLED = auto()

class BrowserCrash(Exception):
    pass

class EvgaBrowser:

    def __init__(self, product_number: str, payment_info, cookies, thread_index, proxy_queue: ProxyQueue, portable=False):
        self.proxy_queue = proxy_queue
        self.index = thread_index
        self.product = product_number
        self.cookies = cookies
        self.cc = payment_info
        self.crash = False
        proxy_address = None
        if proxy_queue:
            proxy_address = self.proxy_queue.get_next_proxy(self.index)
        self.browser = self.setup_browser(
            headless=False, 
            proxy_address=proxy_address
        )
        if not portable:
            self.login()

    @classmethod
    def portable_login(cls, cookies):
        # Combines a few other existing functions, but initializes a simple browser object within itself
        # This is used before starting multiple threads, so they all don't try to login separately
        # Returns true if logged in
        evga = cls(None, None, cookies, 0, None, True)
        if not evga.load_page(cfg.store_homepage): return False
        evga.inject_cookies()
        if not evga.load_page(cfg.store_homepage): return False
        logged_in = evga.verify_login()
        evga.close(True)
        return logged_in

    @classmethod
    def setup_browser(cls, headless=False, proxy_address=None):
        opts = Options()
        opts.headless = headless
        capabilities = ProxyQueue.define_firefox_proxy(proxy_address)
        browser = webdriver.Firefox(
            options=opts, 
            executable_path=get_geckodriver_path(), 
            log_path=get_file_path('geckodriver.log'), 
            capabilities=capabilities
        )
        return browser

    def start_watch(self):
        # MAIN LOOP
        while True:
            load_success = self.load_product_page()
            if not load_success or self.website_is_down() or not self.verify_login():
                if not self.restart():
                    self.browser.quit()
                    return BrowserStatus.KILLED
                self.login()
                if not self.verify_login():
                    return BrowserStatus.LOGOUT
            if self.product_in_stock():
                return BrowserStatus.IN_STOCK

    def inject_cookies(self):
        for cookie in self.cookies:
            self.browser.add_cookie(cookie)

    def login_load_attempt(self, attempt=0):
        load_success = self.load_product_page()
        if not load_success:
            if attempt < 3:
                attempt += 1
                self.restart()
                self.login_load_attempt(attempt)
                return
            else:
                raise BrowserCrash

    def login(self):
        # Access stored cookies and inject into browser cache.
        self.login_load_attempt()
        self.browser.set_window_position(self.index * 15, self.index * 15)
        self.inject_cookies()
        if not self.load_product_page():
            self.login()

    def restart(self):
        # Close & start new browser, for when website crashes
        # Aborts thread and returns False if there's no proxies left to use
        self.close(True)
        if self.index == 0 or self.proxy_queue.size() > 0:
            self.browser = self.setup_browser(
                headless=False,
                proxy_address=self.proxy_queue.get_next_proxy(self.index))
            return True
        print(strings.no_proxies_left)
        return False

    def close(self, immediately=False):
        # Close browser window
        # Use `immediately` arg to skip user prompt
        # Prompt allows user to continue through checkout if script fails
        if not immediately:
            input("WARNING: Script has stopped running. Press enter to close browser")
        self.browser.quit()

    def add_to_cart(self, retry=3):
        # Attempt click "Add to Cart"
        # Doesn't always appear immediately, so check a couple times
        # Must be currently on a loaded product page
        if retry == 0: return False
        try:
            self.browser.find_element_by_id(cfg.add_to_cart).click()
            self.browser.set_window_position(self.index * 15 + 600, self.index * 15)
            print('Added to cart!')
            return True
        except:
            if debug: print('no add to cart!')
            retry -= 1
            return self.add_to_cart(retry)

    def verify_login(self):
        # Look for logged-in UI element "Welcome, <username>" three times in case it doesn't immediately appear
        for _ in range(3):
            try:
                if self.browser.find_element_by_id(cfg.login_status_true): return True
            except:
                if debug: print('no login detected')
                sleep(2)
        return False

    def website_is_down(self):
        # Look for link unique to "We're sorry, website down" page
        for _ in range(2):
            source = self.browser.page_source
            # Look for specific terms in the various error pages displayed during server crashes
            for baddie in crash_indicators:
                if baddie in source: return True
            if debug: print('Login failed but error page is not detected...')
        return False

    def __threaded_page_load(self, url):
        try:
            self.browser.get(url)
            self.crash = False
        except:
            self.crash = True

    def load_page(self, url, timeout=45):
        # Return bool of whether the page loaded within timeout
        thread = Thread(target=self.__threaded_page_load, args=(url, ), daemon=True)
        thread.start()
        start = datetime.now()
        while True:
            if not thread.is_alive():
                if self.crash: 
                    return False
                else: 
                    return True
            delta = datetime.now() - start
            if delta.total_seconds() > timeout:
                return False
            
    def load_product_page(self):
        # Attempt to load page, return success state
        url = cfg.product_page.format(self.product)
        return self.load_page(url)


    def wait_and_click_id(self, element_id: str, duration=1):
        # Loop until the UI element is found, then click it
        while True:
            try:
                self.browser.find_element_by_id(element_id).click()
                return
            except:
                if debug:
                    print('Waiting for ID: ' + element_id)
                sleep(duration)

    def wait_and_click_class(self, element_class, index, duration=1):
        while True:
            try:
                result = self.browser.find_elements_by_class_name(element_class)
                result[index].click()
                break
            except:
                if debug:
                    print('Waiting for Class: ' + element_class)
                    traceback.print_exc()
                sleep(duration)

    def click_continue(self):
        # Same "Continue" button is used in several places
        return self.wait_and_click_id(cfg.continue_button_initial, duration=0.2)

    def product_out_of_stock(self):
        # Check for "OUT OF STOCK" prompt
        try:
            if self.browser.find_element_by_id(cfg.out_of_stock): return True
        except:
            if debug: print('"Out of stock" not found')
        return False

    def product_in_stock(self):
        # Try to find the "Add to Cart" button multiple times, in case it doesn't load immediately
        for _ in range(2):
            try:
                if self.browser.find_element_by_id(cfg.add_to_cart): return True
            except:
                if debug: print('"Add to cart" not found')
        return False

    def populate_credit_card(self):
        try:
            # Enter text fields
            self.browser.find_element_by_id(cfg.name_on_card).send_keys(self.cc.name)
            self.browser.find_element_by_id(cfg.card_number).send_keys(self.cc.number)
            self.browser.find_element_by_id(cfg.card_cvv).send_keys(self.cc.verification)
            # Select dropdown expiration
            Select(self.browser.find_element_by_id(cfg.card_exp_month)).select_by_value(self.cc.exp_month)
            Select(self.browser.find_element_by_id(cfg.card_exp_year)).select_by_value(self.cc.exp_year)
            # Click continue
            self.browser.find_element_by_id(cfg.continue_button_card).click()
        except Exception as error:
            if debug: print(error)
            if debug: traceback.print_exc()
            input('WARNING: Credit card info not populated properly!! \nScript has been paused. Complete purchase manually. \nHit enter to close browser window.')

    def wait_for_captcha(self):
        print(strings.captcha_time)
        captcha = self.browser.find_element_by_xpath(cfg.captcha_iframe)
        self.browser.switch_to.frame(captcha)
        while True:
            try:
                sleep(1)
                checkbox = self.browser.find_element_by_id('recaptcha-anchor')
                checked = checkbox.get_attribute('aria-checked')
                if checked == 'true':
                    self.browser.switch_to.default_content()
                    break
            except KeyboardInterrupt:
                return
            except:
                if debug: traceback.print_exc()
                continue

    def go_through_checkout(self):
        try:
            # First page of checkout
            while not self.load_page(cfg.checkout_page):
                continue
            # Click confirm address
            self.wait_and_click_class(cfg.continue_button_checkout, 0); sleep(2)
            # Click confirm address adjustment
            self.wait_and_click_class(cfg.continue_button_checkout, 2)
            # Click agree to terms
            self.wait_and_click_id(cfg.agree_to_terms)
            # Change -1 to 0 to select cheapest shipping method
            self.browser.find_elements_by_xpath(cfg.ship_speed_select)[-1].click()
            # Wait for user to complete captcha
            self.wait_for_captcha()
            # # Continue to payment
            self.click_continue()
            # # Choose Credit Card
            self.wait_and_click_id(cfg.credit_selection)
            # # Continue to card entry
            self.click_continue()
            # # Enter CC info
            self.populate_credit_card()
            # CC verifcation appears, wait to resolve then click agree
            self.wait_and_click_id(cfg.credit_card_verification)
            # COMPLETE PURCHASE
            # self.click_continue()
        except Exception as error:
            if debug: print(error)
            if debug: traceback.print_exc()
            input('WARNING: Checkout process failed!! \nScript has been paused. Complete purchase manually. \nHit enter to close browser window.')

from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import WebDriverException
from utils import get_file_path
from time import sleep
import platform

debug = False

class EvgaBrowser:

    def __init__(self, product_number: str, payment_info, cookies, thread_index=None):
        self.browser = self.setup_browser()
        self.product = product_number
        self.index = thread_index
        self.cookies = cookies
        self.cc = payment_info
        self.login()

    @classmethod
    def portable_login(cls, cookies):
        # Combines a few other existing functions, but runs without instantiating a class
        # This is used before starting multiple threads, so they all don't try to login separately
        # Returns true if logged in
        url = 'https://www.evga.com/products/feature.aspx'
        browser = cls.setup_browser(False)
        browser.get(url)
        for cookie in cookies:
            browser.add_cookie(cookie)
        browser.get(url)
        for _ in range(3):
            try:
                if browser.find_element_by_id('pnlLoginBoxLogged'): 
                    browser.quit()
                    return True
            except:
                if debug: print('no login detected')
                sleep(2)
        browser.quit()
        return False

    @classmethod
    def setup_browser(cls, headless=False):
        opts = Options()
        opts.headless = headless
        if platform.system() == 'Windows':
            browser = Firefox(options=opts, executable_path=get_file_path('geckodriver.exe'), log_path=get_file_path('geckodriver.log'))
        else:
            browser = Firefox(options=opts, executable_path=get_file_path('geckodriver'), log_path=get_file_path('geckodriver.log'))
        return browser

    def login(self):
        # Access stored cookies and inject into browser cache.
        self.load_product_page()
        self.browser.set_window_position(self.index * 15, self.index * 15)
        for cookie in self.cookies:
            self.browser.add_cookie(cookie)
        self.load_product_page()

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
            self.browser.find_element_by_id('LFrame_btnAddToCart').click()
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
                if self.browser.find_element_by_id('pnlLoginBoxLogged'): return True
            except:
                if debug: print('no login detected')
                sleep(2)
        return False

    def website_is_down(self):
        # Look for link unique to "We're sorry, website down" page
        for _ in range(2):
            source = self.browser.page_source
            # Look for specific terms in the various error pages displayed during server crashes
            if 'error while requesting your page' in source or \
                'internet connection problem to our website.' in source or \
                'email our web team' in source: 
                return True
            if debug: print('Login failed but error page is not detected...')
        return False

    def load_product_page(self, product_number=None):
        if not product_number:
            product_number = self.product
        try:
            self.browser.get('https://www.evga.com/products/product.aspx?pn=' + product_number)
        except WebDriverException:
            # If website fails to load, try and try again
            self.load_product_page()
            return

    def wait_and_click_id(self, element_id: str, duration=1, ):
        # Loop until the UI element is found, then click it
        while True:
            try:
                self.browser.find_element_by_id(element_id).click()
                return
            except:
                if debug:
                    print('Waiting for ID: ' + element_id)
                sleep(duration)

    def click_continue(self):
        # Same "Continue" button is used in several places
        return self.wait_and_click_id('ctl00_LFrame_btncontinue', duration=0.2)

    def product_out_of_stock(self):
        # Check for "OUT OF STOCK" prompt
        try:
            if self.browser.find_element_by_id('LFrame_pnlNotify'): return True
        except:
            if debug: print('"Out of stock" not found')
        return False

    def product_in_stock(self):
        # Try to find the "Add to Cart" button multiple times, in case it doesn't load immediately
        for _ in range(2):
            try:
                if self.browser.find_element_by_id('LFrame_btnAddToCart'): return True
            except:
                if debug: print('"Add to cart" not found')
        return False

    def populate_credit_card(self):
        try:
            # Enter text fields
            self.browser.find_element_by_id('ctl00_LFrame_txtNameOnCard').send_keys(self.cc.name)
            self.browser.find_element_by_id('ctl00_LFrame_txtCardNumber').send_keys(self.cc.number)
            self.browser.find_element_by_id('ctl00_LFrame_txtCvv').send_keys(self.cc.verification)
            # Select dropdown expiration
            Select(self.browser.find_element_by_id('ctl00_LFrame_ddlMonth')).select_by_value(self.cc.exp_month)
            Select(self.browser.find_element_by_id('ctl00_LFrame_ddlYear')).select_by_value(self.cc.exp_year)
            # Click continue
            self.browser.find_element_by_id('ctl00_LFrame_ImageButton2').click()
        except Exception as error:
            if debug: print(error)
            input('WARNING: Credit card info not populated properly!! \nScript has been paused. Complete purchase manually. \nHit enter to close browser window.')

    def go_through_checkout(self):
        try:
            # First page of checkout
            self.browser.get('https://secure.evga.com/Cart/Checkout_Shipping.aspx')
            # Click confirm address
            self.browser.find_elements_by_class_name('btnCheckoutContinue')[0].click(); sleep(1)
            # Click confirm address adjustment
            self.browser.find_elements_by_class_name('btnCheckoutContinue')[2].click(); sleep(1)
            # Click agree to terms
            self.wait_and_click_id('cbAgree')
            # Change -1 to 0 to select cheapest shipping method
            self.browser.find_elements_by_xpath("//input[@name='rdoShipFee']")[-1].click()
            # Continue to payment
            self.click_continue()
            # Choose Credit Card
            self.wait_and_click_id('rdoCreditCard')
            # Continue to card entry
            self.click_continue()
            # Enter CC info
            self.populate_credit_card()
            # CC verifcation appears, wait to resolve then click agree
            self.wait_and_click_id('ctl00_LFrame_cbAgree')
            # COMPLETE PURCHASE
            self.click_continue()
        except Exception as error:
            if debug: print(error)
            input('WARNING: Checkout process failed!! \nScript has been paused. Complete purchase manually. \nHit enter to close browser window.')

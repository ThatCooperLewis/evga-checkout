from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import WebDriverException
from login import save_login_cookies, get_login_cookies
from payment_setup import PaymentInfo
from time import sleep
import json
import sys
import platform
import threading
import queue

debug = False  # True == more verbose output
spacer = '--------------' # Easier parsing of output

class EvgaBrowser:

    def __init__(self, product_number: str, payment_info: PaymentInfo, thread_index=None):
        if platform.system() == 'Windows':
            self.browser = Firefox(executable_path='geckodriver.exe')
        else:
            self.browser = Firefox(options=Options(), executable_path='geckodriver')
        self.product = product_number
        self.index = thread_index
        self.cc = payment_info
        self.login()

    @classmethod
    def headless_login(cls):
        # Combines a few other existing functions, but runs it in headless mode without instantiating a class
        # This is used before starting multiple threads, so they all don't try to login separately
        opts = Options()
        opts.headless = True
        url = 'https://www.evga.com/products/feature.aspx'
        cookies = get_login_cookies()
        if platform.system() == 'Windows':
            browser = Firefox(options=opts, executable_path='geckodriver.exe')
        else:
            browser = Firefox(options=opts, executable_path='geckodriver')
        browser.get(url)
        for cookie in cookies:
            browser.add_cookie(cookie)
        browser.get(url)
        for _ in range(3):
            try:
                if browser.find_element_by_id('pnlLoginBoxLogged'): return True
            except:
                if debug: print('no login detected')
                sleep(2)
        return False

    def login(self):
        # Access stored cookies and inject into browser cache.
        cookies = get_login_cookies()
        self.load_product_page()
        self.browser.set_window_position(self.index * 15, self.index * 15)
        for cookie in cookies:
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
            try:
                if self.browser.find_element_by_link_text('email our web team'): return True
            except:
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

#################################
#      THREADING FUNCTIONS      #
#################################

def resume_paused_threads(instance_count, thread_input):
    # Send signal to all threads to resume refreshing, after login attempt succeeds
    for _ in range(instance_count):
        thread_input.put('resume')

def close_unused_threads(good_instance, instance_count, thread_input):
    # Send signal to close thread based on successful browser instance
    # If instance does not match the successful thread, it closes
    for _ in range(instance_count):
        thread_input.put(good_instance)


def threaded_loop(sku, payment, index, thread_output, thread_input):
    evga = EvgaBrowser(sku, payment, index)
    while True:
        # Refresh page until product in-stock or user is logged-out
        # If logged-out, send login signal and wait for resume signal
        # If in-stock, submit browser class for checkout process, then wait for instance success signal
        evga.load_product_page()
        if not evga.verify_login():
            if evga.website_is_down(): continue
            thread_output.put('login')
            while True:
                if thread_input.qsize() > 0 and thread_input.get():
                    evga.login()
                    break
            continue
        if evga.product_out_of_stock(): continue
        if evga.product_in_stock():
            thread_output.put(evga)
            break
    while True:
        # Wait for instance success signal
        # If this thread is not the successful instance, close window to reduce CPU load.
        if thread_input.qsize() > 0:
            good_index = thread_input.get()
            if good_index != index: evga.close(True)
            break

#################################
#          MAIN LOOP            #
#################################

def loop(sku: str, instance_count: int, payment: PaymentInfo):
    # Setup threads for X number of browser instances
    # Wait for login failure or in-stock success
    # Handle failures & successes using Queue signals to/from threads
    print('Confirming login status, please wait...')
    if not EvgaBrowser.headless_login():
        print("There was an issue logging in. Please try again or refer to documentation.")
        sleep(15)
        exit()
    print('Opening browser windows...')
    thread_output = queue.Queue() # For threads to deliver messages up to main loop
    thread_input = queue.Queue()  # For main loop to send resume/exit messages to threads 
    for index in range(instance_count):
        thread = threading.Thread(target=threaded_loop, args=(sku, payment, index, thread_output, thread_input, ), daemon=True)
        thread.start()
    checkout_started = False
    while True:
        if not checkout_started and (thread_output.qsize() > 0):
            queue_item = thread_output.get()
            if type(queue_item) is str:
                # Run a new window to login & store cookies,
                # send resume-refresh signal to all threads,
                # then clear queue of other login failures
                print(spacer)
                print('ERROR: Cannot login. Running login script...')
                save_login_cookies()
                resume_paused_threads(instance_count, thread_input)
                thread_output.queue.clear()
            else:
                # Use successful instance to continue checkout
                # Asynchronously close all unsuccessful windows
                print(spacer)
                print('Product is in stock!')
                evga = queue_item
                if evga.add_to_cart():
                    checkout_started = True
                    threading.Thread(target=close_unused_threads, args=(evga.index, instance_count, thread_input, ), daemon=True).start()
                    evga.go_through_checkout()
                    print('Checkout process complete!')
                break

def input_sku():
    sku = ''
    while sku == '':
        sku = input('Enter product number, then press Enter: ')
    return sku

def input_instance_count():
    instance_count = ''
    while instance_count == '':
        instance_count = input('Enter number of instances, then press Enter: ')
    try:
        return int(instance_count)
    except ValueError:
        print('[ERROR] Instance count must be a whole number (ex. 1, 12, 25)')
        return input_instance_count()

if __name__ == "__main__":
    try:
        # TODO: Save login as encrypted file
        payment = PaymentInfo()
        if len(sys.argv) == 3:
            instance_count = sys.argv.pop()
            sku = sys.argv.pop()
            loop(sku, int(instance_count), payment)
        else:
            sku = input_sku()
            instance_count = input_instance_count()
            loop(sku, instance_count, payment)
        print('Script complete. This window is safe to close.')
    except Exception as err:
        print(spacer)
        print("Uncaught error occurred. Please report the output below.")
        print(spacer)
        print(err)
        while True:
            pass
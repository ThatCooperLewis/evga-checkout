from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import Select
from login import save_login_cookies
import credit_card as cc
from time import sleep
import json
import sys

import threading
import queue


debug = False # True == more verbose output
spacer = '--------------'
class EvgaBrowser:

    def __init__(self, product_number: str, thread_index=None):
        self.browser = Firefox(options=Options())
        self.product = product_number
        self.index = thread_index
        self.login()

    def login(self):
        # Access stored cookies and inject into browser cache.
        try:
            with open('cookies.json', 'r') as file:
                cookies = json.load(file)
        except:
            print("Error opening cookies.json! Run setup to store user cache.")
            self.close(True)
        self.load_product_page()
        for cookie in cookies:
            self.browser.add_cookie(cookie)
        self.load_product_page()

    def close(self, immediately=False):
        # Close browser window
        # Use `immediately` arg to skip user prompt
        # Prompt allows user to continue through checkout if script fails
        if not immediately:
            input("WARNING: Script has stopped running. Press enter to close browser")
        self.browser.close()

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

    def load_product_page(self, product_number=None):
        if not product_number:
            product_number = self.product
        self.browser.get('https://www.evga.com/products/product.aspx?pn=' + product_number)

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
            self.browser.find_element_by_id('ctl00_LFrame_txtNameOnCard').send_keys(cc.name)
            self.browser.find_element_by_id('ctl00_LFrame_txtCardNumber').send_keys(cc.number)
            self.browser.find_element_by_id('ctl00_LFrame_txtCvv').send_keys(cc.verification)
            # Select dropdown expiration
            Select(self.browser.find_element_by_id('ctl00_LFrame_ddlMonth')).select_by_value(cc.exp_month)
            Select(self.browser.find_element_by_id('ctl00_LFrame_ddlYear')).select_by_value(cc.exp_year)
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

def resume_paused_threads(instance_count, signal_queue):
    # Send signal to all threads to resume refreshing, after login attempt succeeds
    for _ in range(instance_count):
        signal_queue.put('resume')

def close_unused_threads(good_instance, instance_count, signal_queue):
    # Send signal to close thread based on successful browser instance
    # If instance does not match the successful thread, it closes
    for _ in range(instance_count):
        signal_queue.put(good_instance)


def threaded_loop(sku, index, thread_queue, signal_queue):
    evga = EvgaBrowser(sku, index)
    while True:
        # Refresh page until product in-stock or user is logged-out
        # If logged-out, send login signal and wait for resume signal
        # If in-stock, submit browser class for checkout process, then wait for instance success signal
        evga.load_product_page()
        if not evga.verify_login():
            thread_queue.put('login')
            while True:
                if signal_queue.qsize() > 0 and signal_queue.get():
                    evga.login()
                    break
            continue
        if evga.product_out_of_stock(): continue
        if evga.product_in_stock():
            thread_queue.put(evga)
            break
    while True:
        # Wait for instance success signal
        # If this instance is the good one, break loop to keep it open
        # If not successful instance, close window to reduce CPU load.
        if signal_queue.qsize() > 0:
            good_index = signal_queue.get()
            if good_index == index: break
            else: evga.close(True)

#################################
#          MAIN LOOPS           #
#################################

def multiple_loops(sku, instance_count):
    # Setup threads for X number of browser instances
    # Wait for login failure or in-stock success
    # Handle failures & successes using Queue signals to/from threads
    print('Broswer windows now opening. Hit Crtl-C to stop this script.')
    thread_queue = queue.Queue() # For threads to deliver messages up to main loop
    signal_queue = queue.Queue() # For main loop to send resume/exit messages to threads 
    for index in range(instance_count):
        thread = threading.Thread(target=threaded_loop, args=(sku, index, thread_queue, signal_queue, ), daemon=True)
        thread.start()
    checkout_started = False
    while True:
        if not checkout_started and (thread_queue.qsize() > 0):
            queue_item = thread_queue.get()
            if type(queue_item) is str:
                # Run a new window to login & store cookies,
                # send resume-refresh signal to all threads,
                # then clear queue of other login failures
                print(spacer)
                print('ERROR: Cannot login. Running login script...')
                save_login_cookies()
                resume_paused_threads(instance_count, signal_queue)
                thread_queue.queue.clear()
            else:
                # Use successful instance to continue checkout
                # Asynchronously close all unsuccessful windows
                print(spacer)
                print('Product is in stock!')
                evga = queue_item
                if evga.add_to_cart():
                    checkout_started = True
                    threading.Thread(target=close_unused_threads, args=(evga.index, instance_count, signal_queue, ), daemon=True).start()
                    evga.go_through_checkout()
            break

def loop(sku: str):
    print('Broswer windows now opening. Hit Crtl-C to stop this script.')
    evga = EvgaBrowser(sku)
    while True:
        evga.load_product_page()
        if not evga.verify_login(): break 
        if evga.product_out_of_stock(): continue
        if evga.add_to_cart():
            evga.go_through_checkout()
            break

    evga.close()
    quit()


if __name__ == "__main__":
    if len(sys.argv) == 3:
        instance_count = sys.argv.pop()
        sku = sys.argv.pop()
        multiple_loops(sku, int(instance_count))
    elif len(sys.argv) == 2:
        loop(sys.argv.pop())
    else:
        sku = input('Enter product number, then press Enter: ')
        instance_count = input('Enter quantity of browser windows, then press enter')
        print(spacer)
        try:
            multiple_loops(sku, int(instance_count))
        except ValueError:
            loop(sku)
    print('Goodbye.')
    
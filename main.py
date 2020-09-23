from payment_setup import PaymentInfo
from evga_browser import EvgaBrowser
from login import save_login_cookies, get_login_cookies
from utils import input_instance_count, input_sku
from time import sleep
import threading
import queue
import sys


debug = False  # True == more verbose output
spacer = '--------------' # Easier parsing of output

#################################
#      THREADING FUNCTIONS      #
#################################


def threaded_loop(sku, payment, cookies, index, thread_output, thread_input):
    evga = EvgaBrowser(sku, payment, cookies, index)
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

def resume_paused_threads(instance_count, thread_input):
    # Send signal to all threads to resume refreshing, after login attempt succeeds
    for _ in range(instance_count):
        thread_input.put('resume')

def close_unused_threads(good_instance, instance_count, thread_input):
    # Send signal to close thread based on successful browser instance
    # If instance does not match the successful thread, it closes
    for _ in range(instance_count):
        thread_input.put(good_instance)


#################################
#          MAIN LOOP            #
#################################

def loop(sku: str, instance_count: int, payment: PaymentInfo):
    # Setup threads for X number of browser instances
    # Wait for login failure or in-stock success
    # Handle failures & successes using Queue signals to/from threads
    print(spacer)
    print('Confirming login status, please wait...')
    print('If this is taking a long time, EVGA store is likely slugging/crashed.')
    print('You may have to check manually and run again.')
    cookies = get_login_cookies()
    if not EvgaBrowser.headless_login(cookies):
        print("There was an issue logging in. Please try again or refer to documentation.")
        sleep(15)
        exit()
    print('Login confirmed')
    print(spacer)
    print('Opening browser windows...')
    thread_output = queue.Queue() # For threads to deliver messages up to main loop
    thread_input = queue.Queue()  # For main loop to send resume/exit messages to threads 
    for index in range(instance_count):
        thread = threading.Thread(target=threaded_loop, args=(sku, payment, cookies, index, thread_output, thread_input, ), daemon=True)
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

if __name__ == "__main__":
    try:
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
        print(spacer + "\nUncaught error occurred. Please report the output below.\n" + spacer)
        print(err)
        while True:
            pass
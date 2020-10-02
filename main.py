from time import sleep
import threading
import traceback
import queue
import sys

from evga_browser import BrowserStatus as Status
from evga_browser import BrowserCrash
from payment_setup import PaymentInfo
from evga_browser import EvgaBrowser
from proxy_queue import ProxyQueue
import strings
import login
import utils

debug = False  # True == more verbose output

#################################
#      THREADING FUNCTIONS      #
#################################

def threaded_loop(sku, payment, cookies, index, thread_output, thread_input, proxy_queue):
    # Call loop to refresh page until product in-stock or user is logged-out
    # If logged-out, send login signal and wait for resume signal
    # If in-stock, submit browser class for checkout process, then wait for instance success signal
    # If "killed", the thread has run out of proxies and closes quietly
    try:
        evga = EvgaBrowser(sku, payment, cookies, index, proxy_queue)
        # Part 1 - Refresh until in stock
        while True:
            status = evga.start_watch()
            if status is Status.IN_STOCK:
                thread_output.put(evga)
                break
            elif status is Status.KILLED:
                raise KeyboardInterrupt
            else:
                thread_output.put('login')
                while True:
                    if thread_input.qsize() > 0:
                        if not evga.restart():
                            raise KeyboardInterrupt
                        evga.login()
                        break
        # Part 2 - Wait for instance success signal
        while True:
            if thread_input.qsize() > 0:
                good_index = thread_input.get()
                if type(good_index) is not str:
                    if good_index != index: evga.close(True)
                    else: utils.alert_sound()
                    break
    except BrowserCrash:
        print(strings.medium_spacer)
        print(strings.instance_lost_pt1.format(index))
        print('BrowserCrash: either the proxy list ran out, or instance failed to login')
        print(strings.instance_lost_pt2)
        print(strings.medium_spacer)
    except KeyboardInterrupt:
        pass 
    except:
        print(strings.medium_spacer)
        print(strings.instance_lost_pt1.format(index))
        traceback.print_exc()
        print(strings.instance_lost_pt2)
        print(strings.medium_spacer)

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
    print(strings.spacer)
    print(strings.login_confirmation)
    proxies = ProxyQueue()
    if proxies.queue and instance_count > 1:
        print('Found {} proxies available to use.'.format(proxies.size()))
    cookies = login.get_login_cookies()
    if not EvgaBrowser.portable_login(cookies):
        print("There was an issue logging in. Please try again or refer to documentation.")
        input('Press enter to overwrite local cookies & attempt login, or close window: ')
        cookies = login.save_login_cookies()
    print('Login confirmed')
    print(strings.spacer)
    print('Opening browser windows... ', end='')
    thread_output = queue.Queue() # For threads to deliver messages up to main loop
    thread_input = queue.Queue()  # For main loop to send resume/exit messages to threads 
    for index in range(instance_count):
        thread = threading.Thread(target=threaded_loop, args=(sku, payment, cookies, index, thread_output, thread_input, proxies, ), daemon=True)
        thread.start()
    checkout_started = False
    print('OK!')
    print(strings.instaces_running)
    while True:
        if not checkout_started and (thread_output.qsize() > 0):
            queue_item = thread_output.get()
            if type(queue_item) is str:
                # Run a new window to login & store cookies,
                # send resume-refresh signal to all threads,
                # then clear queue of other login failures
                print(strings.spacer)
                print('ERROR: Cannot login. Running login script...')
                _ = login.save_login_cookies()
                resume_paused_threads(instance_count, thread_input)
                thread_output.queue.clear()
            else:
                # Use successful instance to continue checkout
                # Asynchronously close all unsuccessful windows
                print(strings.spacer)
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
            sku = utils.input_sku()
            instance_count = utils.input_instance_count()
            loop(sku, instance_count, payment)
        print(strings.script_complete)
    except KeyboardInterrupt:
        print(strings.stopping_instances)
    except Exception as err:
        print(strings.spacer + "\nUncaught error occurred.\n")
        utils.log_error()
        print(strings.script_complete)
        while True:
            pass
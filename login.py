from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
from evga_browser import EvgaBrowser
from time import sleep
from utils import get_file_path
import platform
import json
import traceback
from selenium.common.exceptions import NoSuchElementException, InvalidSessionIdException, WebDriverException
json_path = get_file_path('cookies.json')

def save_login_cookies():
    # Open new browser window to EVGA login
    # Wait for login sequence (return to homepage) then store cookies
    # Close window & quit once complete
    cookies = None
    evga = EvgaBrowser(None, None, None, 0, None, True)
    browser = evga.browser
    print('---------------------------------------------')
    print('Please finish login sequence in browser window. It will close automatically.')
    print('If you already have cookies saved and want to restart the problematic instance instead,')
    print("close the login window (if it's a proxied instance, a new proxy will be chosen).")
    if not evga.load_page('https://secure.evga.com/us/login.asp'):
        print('------------------------------------------')
        print('ERROR: Login page failed to load. This may be a proxy issue.')
        input('Hit enter to abort login attempt and use existing cookies')
        print('Restarting affected instances...')
        print('-----------------------------------------')
        return None
    while True:
        try: 
            if browser.find_element_by_id('cbp-hrmenu'): 
                cookies = browser.get_cookies()
                break
        except NoSuchElementException: 
            sleep(1)
        except InvalidSessionIdException: break
        except WebDriverException: break

    if cookies:
        with open(json_path, 'w+') as file:
            json.dump(cookies, file)
            file.close()
        print('New user login was successfully cached.')
        browser.close()
        return cookies
    else:
        print('Restarting affected instances...')
        print('-------------------------------')
        return None 

def get_login_cookies():
    try:
        with open(json_path, 'r') as file:
            return json.load(file)
    except:
        return save_login_cookies()

if __name__ == "__main__":
    _ = save_login_cookies()
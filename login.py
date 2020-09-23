from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
from evga_browser import EvgaBrowser
from time import sleep
from utils import get_file_path
import platform
import json

json_path = get_file_path('cookies.json')

def save_login_cookies():
    # Open new browser window to EVGA login
    # Wait for login sequence (return to homepage) then store cookies
    # Close window & quit once complete
    browser = EvgaBrowser.setup_browser()
    print('Please finish login sequence in browser window. It will close automatically.')
    browser.get('https://secure.evga.com/us/login.asp')
    while True:
        try: 
            if browser.find_element_by_id('cbp-hrmenu'): break
        except: 
            sleep(1)
    cookies = browser.get_cookies()
    with open(json_path, 'w+') as file:
        json.dump(cookies, file)
        file.close()
    print('User was successfully cached.')
    browser.close()
    return cookies

def get_login_cookies():
    try:
        with open(json_path, 'r') as file:
            return json.load(file)
    except:
        return save_login_cookies()

if __name__ == "__main__":
    _ = save_login_cookies()
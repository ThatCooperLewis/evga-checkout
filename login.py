from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
from time import sleep
import platform
import json

def save_login_cookies():
    # Open new browser window to EVGA login
    # Wait for login sequence (return to homepage) then store cookies
    # Close window & quit once complete
    opts = Options()
    if platform.system() == 'Windows':
        browser = Firefox(options=opts, executable_path='geckodriver.exe')
    else:
        browser = Firefox(options=opts, executable_path='geckodriver')
    print('Please finish login sequence in browser window. It will close automatically.')
    browser.get('https://secure.evga.com/us/login.asp')
    while True:
        try: 
            if browser.find_element_by_id('cbp-hrmenu'): break
        except: 
            sleep(1)
    cookies = browser.get_cookies()
    with open('cookies.json', 'w+') as file:
        json.dump(cookies, file)
        file.close()
    print('User was successfully cached.')
    browser.close()
    return cookies

def get_login_cookies():
    try:
        with open('cookies.json', 'r') as file:
            return json.load(file)
    except:
        return save_login_cookies()

if __name__ == "__main__":
    _ = save_login_cookies()
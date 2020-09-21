from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
import json
from time import sleep

def save_login_cookies():
    # Open new browser window to EVGA login
    # Wait for login sequence (return to homepage) then store cookies
    # Close window & quit once complete
    opts = Options()
    browser = Firefox(options=opts)
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
    print('User is cached. Continue onto main loop.')
    browser.close()

if __name__ == "__main__":
    save_login_cookies()
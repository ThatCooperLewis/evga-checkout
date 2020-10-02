from selenium import webdriver
from queue import Queue
import requests
import json


class ProxyQueue:

    def __init__(self):
        self.queue = self.__get_proxy_queue()

    def __get_proxy_queue(self):
        usa_proxies = Queue()
        try:
            import proxy_config
            email = proxy_config.email
            pw = proxy_config.pw
        except ModuleNotFoundError:
            print('No proxy configuration found. Using local IP for all instances.')
            return None
        res = requests.get('http://list.didsoft.com/get?email={}&pass={}&pid=http6500&showcountry=yes&https=yes'.format(email, pw))
        # Handle bad request
        if res.status_code != 200:
            print('ERROR: Credentials for proxy service are invalid') 
            return None
        # Filter for US proxies
        empty = True
        with open('proxylist.txt', 'w+') as file:
            for ip in res.text.split('\n'):
                if 'US' in ip:
                    ip = ip.replace('#US','').replace(' | FreeProxy','')
                    file.write(ip + '\n')
                    empty = False
                    usa_proxies.put(ip)
        if empty:
            print('WARNING: No proxy servers found. Using local IP for all instances...')
            return None
        return usa_proxies

    def get_next_proxy(self, index):
        if index > 0 and self.queue and self.queue.qsize() > 0:
            return self.queue.get()
        else:
            return None

    def size(self):
        return self.queue.qsize()

    @classmethod
    def define_firefox_proxy(cls, address):
        if address:
            capabilities = webdriver.DesiredCapabilities.FIREFOX
            capabilities['marionette'] = True
            capabilities['proxy'] = {
                "proxyType": "MANUAL",
                "httpProxy": address,
                "ftpProxy": address,
                "sslProxy": address
            }
            return capabilities
        else:
            return None
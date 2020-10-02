import os, sys, traceback
import time
import platform

from playsound import playsound as play

def get_current_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    elif __file__:
        return os.path.dirname(__file__)

def get_file_path(filename: str):
    file_path = os.path.join(get_current_dir(), filename)
    return file_path

def get_geckodriver_path():
    if platform.system() == 'Windows':
        return get_file_path('geckodriver.exe')
    else:
        return get_file_path('geckodriver')

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

def alert_sound():
    play(get_file_path('sos.mp3'))

def log_error():
    with open(get_file_path('error_log.txt'), 'a+') as file:
        file.write(time.ctime())
        file.write(traceback.format_exc())
        file.write('\n')
        file.close()
    print('Error message has been stored to error_log.txt. Please share with developer.')
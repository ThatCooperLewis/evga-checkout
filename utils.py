import os, sys

def get_current_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    elif __file__:
        return os.path.dirname(__file__)

def get_file_path(filename: str):
    file_path = os.path.join(get_current_dir(), filename)
    return file_path

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
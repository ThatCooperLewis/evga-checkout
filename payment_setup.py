import json
import getpass
import os
import sys
import pyzipper
import warnings
from utils import get_file_path

warnings.filterwarnings("ignore", category=DeprecationWarning) 

zip_path = get_file_path('payment.zip')

class PaymentInfo:

    def __init__(self):
        payment_dict = get_payment_config()

        self.name = payment_dict['name']                 # Full name as appears on card
        self.number = payment_dict['number']             # CC number (digits only, no spaces)
        self.exp_month = payment_dict['exp_month']       # MM
        self.exp_year = payment_dict['exp_year']         # YYYY 
        self.verification = payment_dict['verification'] # 4-digit front of Amex, 3-digit back of other cards

def save_cc():
    print('Please enter credit/debit card information. Data will be saved to a local file.')

    cc_name = input('Full name on card: ')
    cc_num = input('Credit Card # (no spaces, digits only): ')
    cc_month = input("Expiration month (MM): ")
    cc_year = input("Expiration year (YYYY): ")
    cc_verif = input("Verification code: ")

    payment_obj = {
        "name": cc_name,
        "number": cc_num,
        "exp_month": cc_month,
        "exp_year": cc_year,
        "verification": cc_verif,
    }

    pw = get_password_input('Enter new password for encrypted payment file: ')
    with pyzipper.AESZipFile(zip_path, 'w', compression=pyzipper.ZIP_LZMA) as zf:
        zf.writestr('payment.json', json.dumps(payment_obj))
        zf.setpassword(pw)

    print('Payment information encrypted to payment.zip')
    return payment_obj

def get_password_input(prompt: str, confirm=True):
    pw = getpass.getpass(prompt, stream=None)
    if confirm:
        pw2 = getpass.getpass('Confirm paswword: ', stream=None)
        if pw != pw2:
            print("Passwords do not match. Try again...")
            return get_password_input(prompt)
    return bytes(pw, 'utf-8')

def get_payment_config():
    if os.path.isfile(zip_path):
        pw = get_password_input('Enter password to access payment information: ', False)
        with pyzipper.AESZipFile(zip_path) as zf:
            zf.setpassword(pw)
            payment_str = zf.read('payment.json')
            zf.close()
        payment_obj = json.loads(payment_str)
        return payment_obj
    else:
        return save_cc()

if __name__ == "__main__":
    _ = save_cc()
    print('\n--------------')
    print("Lets make sure the bot can unlock the payment info.")
    _ = get_payment_config()
    print("If you see this, that means its working.")
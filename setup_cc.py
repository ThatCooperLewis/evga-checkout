print('Please enter credit/debit card information. Data will be saved to a local file.')

cc_name = input('Full name on card: ')
cc_num = input('Credit Card # (no spaces, digits only): ')
cc_month = input("Expiration month (MM): ")
cc_year = input("Expiration year (YYYY): ")
cc_verif = input("Verification code: ")

with open('credit_card.py', 'w+') as file:
    file.writelines([
        "name = '{}'\n".format(cc_name),
        "number = '{}'\n".format(cc_num),
        "exp_month = '{}'\n".format(cc_month),
        "exp_year = '{}'\n".format(cc_year),
        "verification = '{}'\n".format(cc_verif),
    ])

print('Saved to credit_card.py')
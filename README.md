# EVGA Store Checkout Automator

**NOTE: As of Oct 6th, 2020, this script is no longer effective in purchasing an Nvidia 30 Series card. EVGA has implemented a queue system to prevent automated purchases.**

An automation tool for product status/checkout through the EVGA Store. Supports multiple instances and permanent captcha-free authorization.

I have tested this on MacOS Catalina, using an American Express card, shipping to United States. I cannot promise compatibility with anything else (other mac versions and card types should be fine, idk about international).

## Requirements:

- Rudimentary experience with the command line
- A verified [EVGA account](https://secure.evga.com/us/login.asp) with separate billing/shipping addresses saved on profile (even if they're the same).
  - Make sure to keep your ZIP code to 5 digits, not the full version. My bot anticipates the website correcting your address to the full ZIP. Pretend to go through checkout beforehand to confirm you get that additional prompt for address correction.
- Product number of desired listing the [EVGA Store](https://www.evga.com/products/feature.aspx). This can be found after `?pn=` in the product page's URL. 
- Firefox Quantum 80.0.1 
  - For other versions & troubleshooting, see [geckodriver](#Geckodriver/Firefox) section

## Build

To manually build this app, you need to have Python 3.7+ installed. 

Install requirements

        pip install -r requirements.txt

Create executable

        pyinstaller -F main.py

After this, you'll need to move the appropriate geckodriver file from the root directory into `/dist`.

- `dist/geckodriver.exe` for Windows
- `dist/geckodriver` for MacOS

Double-click on `dist/main` and the program should run. 

1. Enter payment info
2. Complete online login & captcha
3. Enter product number
4. Enter desired # of browser windows

## Advanced CLI Setup

### Setup environment & user configuration

Run `setupMacOS.command` to setup the bot configuration

Two steps require your input:

1. Login Information

    - Your user cookies must be stored locally so the bot can auto-login. You should only need to do this once, but, if the bot loses login status while running, it will trigger this process as well.

    - `setupMacOS` will open a new browser window. Enter information, complete captcha & login. A new file `cookies.json` should now exist in the root directory.

2. Credit/Debit information

    - This bot needs to create a local file with payment information. It will directly access this information to populate into EVGA's website. 
    
    - At no point is this data sent elsewhere. An internet stranger's promise is not very substantial, so if you have reservations, please refer to the source code. `setup_cc.py` (run during setup) is very simple input/filesave, and the bot's only use of `credit_card.py` exists in `main.py`:
        
                import credit_card as cc
                def populate_credit_card(self):
                    # Looks for CC input field on EVGA checkout page
                    # Populates those fields with cc variables

## Simple Usage

Open `runMacOS.command` to start bot. It will prompt you for the product number and # of windows (refer to Multiple Windows section for explanation of instances).

## Advanced Usage

Be sure to define environment using `source venv/bin/activate` before running `main.py` :



`python main.py <product_number> <instance_count(1)>`

### Single instance

To run a single window (more stable for low-spec machines) execute main.py with the product number. For example, to run using the 3080 FTW:

`python main.py 10G-P5-3897-KR`

### Multiple windows

This bot can monitor several instances simultaneously, reducing reaction time. To run multiple browser windows, add the desired quantity after the product number. Default is 1.

`python main.py 10G-P5-3897-KR 10`

Whichever window first detects the product in-stock will complete purchase. The rest will stop loading & exit. 

Keep an eye on all windows, so you can monitor the checkout process once it's triggered.

The quantity is limited by your CPU power (and potenitally a request limit from EVGA, but I haven't found such a limit). Each window will be constantly refreshing. My Late-2019 MBP (i9 9900HK) started chugging around 20 instances.


## Troubleshooting

### Python

Most macOS systems use Python 2 by default. If you're getting errors like `Python: No module named venv`, use `python3` and `pip3` for all appropriate commands.

### Geckodriver/Firefox

Your versions of Firefox and the WebEngine must be synced. If you get weird firefox/gecko/driver issues when launching the script, you likely don't have the right broswer/driver pair.

If you're running the newest version of firefox, get the [most recent WebEngine here](https://github.com/mozilla/geckodriver/releases). Add the `geckodriver` file to the script directory.

On macOS there is an extra step. With a terminal in this script's directory, run this command:

        xattr -r -d com.apple.quarantine geckodriver

For more info on this `xattr` workaround, [refer to these docs](https://firefox-source-docs.mozilla.org/testing/geckodriver/Notarization.html).

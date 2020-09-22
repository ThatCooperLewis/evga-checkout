#!/bin/sh

here="`dirname \"$0\"`"
cd "$here" || exit 1



echo "Intialize environment..."

python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt



echo "Fix geckodriver..."

xattr -r -d com.apple.quarantine geckodriver


echo "Start login process..."

python3 login.py



echo "Setup local configuration..."

python3 payment_setup.py


echo "It is safe to close this window. Open runMacOS.command to run bot."
#!/bin/sh

here="`dirname \"$0\"`"
cd "$here" || exit 1



echo "Intialize environment..."

python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt



echo "Move default geckodriver..."

mv geckodriver venv/bin
xattr -r -d com.apple.quarantine venv/bin/geckodriver


echo "Start login process..."

python3 login.py



echo "Setup local configuration..."

python3 setup_cc.py


echo "It is safe to close this window. Open runMacOS.command to run bot."
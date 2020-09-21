#!/bin/sh

here="`dirname \"$0\"`"
cd "$here" || exit 1


source venv/bin/activate
python3 main.py


echo "It is safe to close this window."
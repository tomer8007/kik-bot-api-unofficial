# Kik Bot API #

This is a modification to kik-bot-api-unofficial and can be used as a spam bot.

## Installation and dependencies ##

First, make sure you are using **Python 3.6+**, not python 2.7 or python 3.9. 


** (Do this before installing the api/more on how to get python 3.8 below.)

If you are using [Termux](https://termux.com/), then use `pkg install libxml2 libxslt` to install `lxml` and `pkg install zlib libpng libjpeg-turbo` to install `pillow` dependencies.

## Installation ## (this may take a while so be patient)

$ git clone -b new https://github.com/Sitiaro/Spambot **

$ pip3 install ./Spambot

## Usage ##

$ cd Spambot

$ python spambot.py

Login with the username and password of your spam account, add it to your friend list by typing 'friend' in the bot's dms and add it to the chat you want to spam. Once you do so, use .spam (no. of messages) to spam the chat.

You can send 'Disconnect' in dms to stop the bot from spamming incase it gets removed from a chat but the spam doesn't stop (in your Terminal). Either this, or you can simply restart the bot and login with different creds since most owners/admins tend to ban such bots.

## For educational purposes only. This may lead to your account getting banned from kik so use it at your own expense. ##


## Replacing python 3.9 with 3.8 ##

(Termux)

Uninstall python -

$ pkg uninstall python

Check the arch of your device cpu using -

$ uname -m

Go to https://github.com/Termux-pod/termux-pod and find the file corresponding to your device's CPU. You should try python_3.8.6_.deb first and then the static version if there is any error.

Download the raw .deb file in termux using web-get.

Make sure you add ?raw=true to the end of the url, or else you'll end up downloading the html file. So 
it'll be something like this -

$ wget https://github.com/Termux-pod/termux-pod/blob/main/arm/python/python_3.8.6_<CPU_ARCH.>.deb?raw=true

(replace <CPU_ARCH.> with your device's cpu)

((Copy pasting this url in your browser after replacing <CPU_ARCH.>, it'll download the package to your system itself. If you do this then follow the below mentioned steps;

$ cd sdcard/Download

$ cp python_3.8.6_<CPU_ARCH.>.deb /$HOME

$ cd $HOME    

Finally, execute the following command in termux -

$ dpkg -i ./python_3.8.6_<CPU_ARCH.>.deb

Once again, replacing <CPU_ARCH.> with your cpu's architecture (for me it was arm).

#!/bin/bash

# This script will create a canned user.
# instadmg POC
# Josh Wisenbaker 7/13/2007 on my ass at SFO

#Make the account
/usr/bin/dscl . -create Users/instadmg
/usr/bin/dscl . -create Users/instadmg home /Users/instadmg
/usr/bin/dscl . -create Users/instadmg shell /bin/bash
/usr/bin/dscl . -create Users/instadmg uid 1024
/usr/bin/dscl . -create Users/instadmg gid 1024
/usr/bin/dscl . -create Users/instadmg realname "Insta DMG"
/usr/bin/dscl . -create Groups/instadmg
/usr/bin/dscl . -create Groups/instadmg gid 1024
/usr/bin/dscl . -passwd Users/instadmg "password"
/usr/sbin/dseditgroup -o edit -a instadmg -t user -n /NetInfo/DefaultLocalNode admin

#Make the home
/usr/bin/ditto /System/Library/User\ Template/English.lproj/ /Users/instadmg
/usr/sbin/chown -R instadmg:instadmg /Users/instadmg

exit 0

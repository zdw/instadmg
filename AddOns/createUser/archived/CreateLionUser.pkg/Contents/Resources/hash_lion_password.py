#!/usr/bin/python
#
# Create 10.7 ShadowHashData for a user.
# Written by Per Olofsson, per.olofsson@gu.se.
# Based on code by Pete Akins, Karl Kuehn, and Greg Neagle.
#
# Version history:
#     0.1: Proof of concept. (PO)
#     0.2: Cleaned up and generalized code. (PO)
#
# TODO:
#     * Add more hash methods.
#     * Handle character encoding.


import sys
import optparse
import random
import struct
import hashlib
import getpass
from Foundation import NSData, \
    NSPropertyListSerialization, \
    NSPropertyListMutableContainers, \
    NSPropertyListBinaryFormat_v1_0


def serialize_hash_dict(hash_dict):
    plist_data, error = \
     NSPropertyListSerialization.dataFromPropertyList_format_errorDescription_(
                            hash_dict, NSPropertyListBinaryFormat_v1_0, None)
    if error:
        # FIXME: Raise an exception instead.
        print >>sys.stderr, error
        return None
    
    return plist_data
    

# Each hash method should take a password string as the argument and return a
# hashed password string.


def salted_sha512(password):
    seedInt = random.randrange(1, 2**31 - 1)
    seedHex = ("%x" % seedInt).upper().zfill(8)
    seedString = struct.pack(">L", seedInt)
    saltedPassword = hashlib.sha512(seedString + password).digest()
    return "%s%s" % (seedString, saltedPassword)
    

# Dictionary of methods and hash functions.
hash_methods = {
    "SALTED-SHA512": salted_sha512,
}


def main(argv):
    p = optparse.OptionParser()
    p.set_usage("""Usage: %prog [options] userdata.plist [password]""")
    p.add_option("-v", "--verbose", action="store_true",
                 help="Verbose output.")
    options, argv = p.parse_args(argv)
    if len(argv) not in (2, 3):
        print >>sys.stderr, p.get_usage()
        return 1
    
    # Read the userdata.plist.
    plist = argv[1]
    
    plist_data = NSData.dataWithContentsOfFile_(plist)
    if not plist_data:
        print >>sys.stderr, "Couldn't read %s" % plist
        return 1
    
    user_plist, plist_format, error = \
     NSPropertyListSerialization.propertyListFromData_mutabilityOption_format_errorDescription_(
                    plist_data, NSPropertyListMutableContainers, None, None)
    
    if error:
        print >>sys.stderr, "Can't read %s: %s" % (plist, error)
        return 1
    
    # Use password on commandline, or ask if one isn't provided.
    try:
        password = argv[2]
    except IndexError:
        while True:
            password = getpass.getpass()
            verify_password = getpass.getpass("Password again: ")
            if password == verify_password:
                break
            else:
                print "Passwords don't match!"
    
    # Hash password with all available methods.
    hashed_passwords = dict()
    for k, m in hash_methods.items():
        hashed_pwd = m(password)
        pwd_data = NSData.alloc().initWithBytes_length_(hashed_pwd, len(hashed_pwd))
        hashed_passwords[k] = pwd_data
    
    # Serialize hashed passwords to a binary plist.
    serialized_passwords = serialize_hash_dict(hashed_passwords)
    if not serialized_passwords:
        return 2
    
    # Write back userdata.plist with ShadowHashData.
    user_plist["ShadowHashData"] = list()
    user_plist["ShadowHashData"].append(serialized_passwords)
    
    plist_data, error = \
     NSPropertyListSerialization.dataFromPropertyList_format_errorDescription_(
                            user_plist, plist_format, None)
    plist_data.writeToFile_atomically_(argv[1], True)
    
    return 0
    

if __name__ == '__main__':
    sys.exit(main(sys.argv))
    

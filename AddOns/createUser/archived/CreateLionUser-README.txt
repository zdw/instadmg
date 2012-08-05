CreateLionUser.pkg
==================

CreateLionUser.pkg is a rewrite of the venerable createUser.pkg for 10.7, in Python. It's a payload free package that can be used to deploy local user accounts, and aims to be compatible with all modular deployment workflows.


Configuring the Package
-----------------------

The package must be configured before it can be deployed. In my example I'll configure it to deploy a local, hidden, admin user named `gadmin`. Start by making a copy of the pkg, and rename it something descriptive like `CreateLionUser_gadmin.pkg`. Then right click on the pkg, Show Package Contents, and navigate to `Contents/Resources`. In here you'll find:

* en.lproj/Description.plist - You can give your package a nice description if you want.
* hash_lion_password.py - Use this tool to set the user's password.
* postflight - This is the main script that will be executed when the package is deployed.
* userdata.plist - This is a property list that you will use to configure the package.

Open up `userdata.plist` in your favorite editor - you can use TextEdit, but I recommend a good programmer's editor such as TextMate or TextWrangler. You can also use Property List Editor or Xcode if you have the developer tools installed.

The following keys can be configured:

`shortname`, string

This is a required key, and should contain the shortname of the user, e.g. `gadmin`.

`RealName`, string

The human readable user name, defaults to the shortname.

`UniqueID`, integer

The user's uid. If one isn't given, the first free uid between 501 and 600 is used.

`PrimaryGroupID`, integer

The user's primary group, defaults to 20 (staff).

`Picture`, string

A loginwindow picture, defaults to `/Library/User Pictures/Fun/Smack.tif`.

`UserShell`, string

Defaults to /bin/bash.

`NFSHomeDirectory`, string

Defaults to `/Users/%u`. The following placeholder substitutions are currently supported:

* `%u` substitute the shortname
* `%n` substitute the UniqueID
* `%l` substitute the first letter of the shortname, in lowercase.
* `%L` substitute the first letter of the shortname, in uppercase.

`GeneratedUID`, string

By default a guid is generated when the user is created, but it can be overriden by setting this string.

`ShadowHashData`, array of data

This is a required key and needs to be set with a special tool, see below.

`IsAdmin`, integer

A 1 means that the user will be made a member of the admin group, a 0 creates a standard user.

`IsHidden`, integer

A 1 means that the user will be hidden from the login window.

`KickstartARD`, integer

A 1 means that the Apple Remote Desktop agent should be kickstarted and access given to the newly created user.


Setting the Password
--------------------

The password needs to be encrypted before it's stored in userdata.plist. Currently this needs to be done from the command line, so start Terminal and cd to the Resources directory (you can do this by typing "cd " (note the space), and then dragging and dropping the Resources folder from the Finder into the Terminal window). Execute the command:

    ./hash_lion_password.py userdata.plist

It'll prompt you for a password, and again to verify, and then update the userdata.plist with the encrypted hash.


Testing the Package
-------------------

Copy the configured package over to a test machine (no really, don't have anything important on this machine), and install the package. To see progress information and any error messages, install it from the command line with -dumplog and -verbose:

    sudo installer -dumplog -verbose -target / -package CreateLionUser_gadmin.pkg

It'll also log output to `/var/log/install.log`. If all is well, verify that the user shows up properly in System Preferences and that you can log in.


Deploying the Package
---------------------

The package should be compatible with InstaDMG, DeployStudio, Absolute Manage, Casper, System Image Utility, and all other modular deployment tools that can install pkgs.


History
-------

* 2011-06-16: First test release.
* 2011-06-17: Second test release.
    * Fixed syntax error in hash_lion_password.py.
    * Fixed missing SCRIPT_DIR path when loading userdata.plist.
* 2011-06-20: Third test release.
    * Flushing Directory Service cache before and after setting the ShadowHashData.
    * Added KickstartARD.


Credits
-------

CreateLionUser.pkg was written by Per Olofsson, per.olofsson@gu.se. It's based on createUser.pkg by Pete Akins, generatePasswordHash.py by Karl Kuehn, and I've borrowed some PyObjC snippets from Greg Neagle.


License
-------

Copyright 2011 Per Olofsson, University of Gothenburg

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

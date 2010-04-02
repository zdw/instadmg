Using the createUser Pacakge.

This package has been created to help automate new local user creation, especially for image maintenance. It allows for a decent amount of flexibility, but also contains defaults for simple operation. It can create a new user for both 10.4 and 10.5 systems, and optionally add it to the admin group . It can be targeted to a different volume so it is very well suited for an automated image creation environment such as InstaDMG, but also is useful for ARD.

How to use createUser

createUser is distributed as a pre-made payload-free package. It utilizes a postflight script that reads its parameters from a text file called USERDATA. This allows a novice to change parameters without concern of messing with the main script. Here's what to do:

1. In Finder, Ctrl-Click on the package and choose "Show Package Contents"
2. Browse to Contents/Resources and open up the "USERDATA" file in your favorite text editor
3. At MINIMUM you need a valid short name and a method to generate password (see GENERATING PASSWORDS below). To ease in validation, it will only accept short names with letters, numbers and underscore that are 1-31 characters. 
4. For most other parameters you can enter in your prescribed values, or leave the options commented (with the pound # symbol at the beginning of the line). Commented options will retain defaults that are likely obvious to most experienced people.
5. Be sure to include quotes around the long name if it has spaces
6. Be sure to remove the pound symbol before an entry if you wish to specify a value. i.e.
	#gid=20
becomes
	gid=20
	
7. Make sure you set the admin value to your preference: 1=add to admin group, 0= don't add to admin group.


Generating Passwords

You have two ways to generate passwords. The RECOMMENDED way is to use the included shadowHash script to pre-generate a valid shadow hash file. Simply save the resultant output to a file called "password_hash" in the resources folder and the package will use it.

From Terminal:
1. type "cd " then drag the Resources folder from the finder into terminal, this will paste the full path of the resources folder into the shell, then hit enter
2. Type the following:
./shadowHash yourpassword>password_hash

This will generate a file named password_hash that is ready to be used for the package. FYI: The password_hash file distributed with this package is set to "password" by default.

You can also include the password as clear text in the USERDATA file, but this is STRONGLY DISCOURAGED as this will be readable by anyone, and the file tends to stay in /Library/Receipts afterward. Seriously don't do it.
_That Being Said_
If you choose this method, you MUST delete the "password_hash" file in the package as the script will use it first if it is there regardless of what you put in the USERDATA file.

Seriously, ask for assistance on a mailing list or the AFP548 forums if the "password_hash" doesn't work for you, we're more than happy to help out.

That's it! Once you have set up the package, you can then insert it into your build train for InstaDMG, and also distribute it using ARD


Notes:

This script is included completely free of charge to use and alter as you wish. I ask for nothing aside from appropriate attribution if you distribute it further. 

Pete Akins. pete.akins@uc.edu

History:

This version, bundled with InstaDMG 1.6b2, includes additional(although commented-out) functionality to initiate ARD access for the newly-created user
version 1.0.3: August 25, 2009 - Updated script to handle 10.6 and clarified documentation. Thanks to Reed Stoner for contributions.
version 1.0.2: May 8, 2008 - Fixed a bug with parsing the shortname
version 1.0.1: May 2, 2008 - Added options for home folder location and ability to hide user from loginwindow
version 1.0: April 2, 2008 - Initial Release
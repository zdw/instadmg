#!/usr/bin/python

import os, unittest, pwd

from checksum_test				import *
from commonConfiguration_test	import *
from displayTools_test			import *
from installerPackage_test		import *
from managedSubprocess_test		import *
from pathHelpers_test			import *
from tempFolderManager_test		import *
from testingHelpers_test		import *
from volumeManager_test			import *

# ToDo: automate finding the tests

if __name__ == "__main__":
#	if os.getuid() == 0:
#		# run as both root, and a user
#		unittest.main(exit=False)
#		os.setuid(pwd.getpwnam(os.getlogin()).pw_uid)
	
	unittest.main()
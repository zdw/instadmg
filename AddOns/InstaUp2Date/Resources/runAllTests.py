#!/usr/bin/python

import unittest, os, sys

from displayTools_test import *
from checksum_test import *
from managedSubprocess_test import *
from tempFolderManager_test import *
from testingHelpers_test import *
from volumeManager_test import *
# ToDo: automate finding the tests

if __name__ == "__main__":
	unittest.main()
#!/usr/bin/python

'''A collection point for hard-coded values that need to be shared between modules'''

import os

pathToInstaDMG			= os.path.normpath(os.path.join(os.path.dirname(__file__), "../../../instadmg.bash"))
pathToInstaDMGFolder	= os.path.dirname(pathToInstaDMG)

standardCatalogFolder	= os.path.normpath(os.path.join(os.path.dirname(__file__), "../CatalogFiles"))

standardCacheFolder		= os.path.join(pathToInstaDMGFolder, "Caches", "InstaUp2DateCache")
standardUserItemsFolder	= os.path.join(pathToInstaDMGFolder, "InstallerFiles", "InstaUp2DatePackages")

legacyOSDiscFolder		= os.path.join(pathToInstaDMGFolder, "InstallerFiles", "BaseOS")
standardOSDiscFolder	= os.path.join(pathToInstaDMGFolder, "InstallerFiles", "InstallerDiscs")

standardOutputFolder	= os.path.join(pathToInstaDMGFolder, "OutputFiles")

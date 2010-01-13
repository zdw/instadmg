#!/bin/bash

#
# instadmg - script to automate creating ASR disk images
#

#
# Maintained by the InstaDMG dev team @ http://code.google.com/p/instadmg/
# Latest news, releases, and user forums @ http://www.afp548.com
#

SVN_REVISION=`/bin/echo '$Revision$' | /usr/bin/awk '{ print $2 }'`
VERSION="1.6b1 (svn revision: $SVN_REVISION)"
PROGRAM=$( (basename $0) )


#<!------------------- Setup Environment ------------------->

IFS=$'\n'

# remove aliases that might be problematic
unset -f unalias
unalias -a
unset -f command

# prevent uninialized vaiables from being used
set -o nounset

# set path to a known path
PATH="/usr/bin:/bin:/usr/sbin:/sbin"
export PATH

# Change the working directory to the one containing the instadmg.bash script
cd "`/usr/bin/dirname "$0"`"

# Environment variables used by the installer command
export COMMAND_LINE_INSTALL=1
export CM_BUILD=CM_BUILD


#<!------------------- Variable Defaults ------------------->

# Set the creation date in a variable so it's consistant during execution.
CREATE_DATE=`/bin/date +%y-%m-%d`

# Default values
DMG_SIZE=300g									# Size of the sparce image, this shoud be large enough
ISO_CODE="en"									# ISO code that installer will use for the install language
DISABLE_CHROOT=false							# Use a chroot jail while installing updates
DISABLE_BASE_IMAGE_CACHING=false				# setting this to true turns off caching
ENABLE_TESTING_VOLUME=false						# setting this and the TESTING_TARGET_VOLUME will erase that volume and write the image onto it
ENABLE_NON_PARANOID_MODE=false					# disable checking image checksums

# Default folders
INSTALLER_FOLDER="./InstallerFiles/BaseOS"		# Images of install DVDs
INSTALLER_DISK=''								# User-supplied path to a specific installer disk
SUPPORTING_DISKS=''								# Array of user-supplied supporting disks to mount

UPDATE_FOLDER="./InstallerFiles/BaseUpdates"	# Combo update first, followed by additional numbered folders
CUSTOM_FOLDER="./InstallerFiles/CustomPKG"		# All other update pkg's
UPDATE_FOLDERS=()								# Array of the folders to pull updates from in the order they should be installed

ASR_FOLDER="./OutputFiles"						# Destination of the ASR images
BASE_IMAGE_CACHE="./Caches/BaseImageCache"		# Cached images named by checksums
LOG_FOLDER="./Logs"
TEMPORARY_FOLDER="/private/tmp"		# DMGs will be mounted at a location inside of this folder
TESTING_TARGET_VOLUME=''						# setting this and the ENABLE_TESTING_VOLUME will erase that volume and write the image onto it

# TODO: make sure that the cached images are not indexed

# Default Names
DMG_BASE_NAME=`/usr/bin/uuidgen`				# Name of the intermediary image

MOUNT_FOLDER_TEMPLATE="InstaDMG_temp_folder.XXXXXX"
MOUNT_POINT_TEMPLATE="mount_point.XXXXXX"
SOURCE_FOLDER_TEMPLATE="package.XXXXXX"

ASR_OUPUT_FILE_NAME="${CREATE_DATE}.dmg"		# Name of the final image file
ASR_FILESYSTEM_NAME="InstaDMG"					# Name of the filesystem in the final image

# Names allowed for the primary installer disk
ALLOWED_INSTALLER_DISK_NAMES=("Mac OS X Install Disc 1.dmg" "Mac OS X Install DVD.dmg")

# Bundle identifier codes to exclude from the chroot system
CHROOT_EXCLUDED_CODES=("edu.uc.daap.createuser.pkg")

#<!-------------------- Working Variables ------------------>
HOST_MOUNT_FOLDER=''					# Enclosing folder for the base image mount point, and othes if not using chroot
TARGET_TEMP_FOLDER=''					# If using chroot packages will be copied into temp folders in here before install

TARGET_IMAGE_MOUNT=''					# Where the target is mounted
TARGET_IMAGE_FILE=''					# Location of the base image dmg if using cached images, the whole image dmg otherwise
TARGET_IMAGE_CHECKSUM=''				# Checksum reported by diskutil for the OS Instal disk image

SHADOW_FILE_LOCATION=''					# Location of the shadow file that is grafted onto the TARGET_IMAGE_MOUNT

CURRENT_OS_INSTALL_FILE=''				# Location of the primary installer disk
CURRENT_OS_INSTALL_MOUNT=''				# Mounted location of the primary installer disk
CURRENT_OS_INSTALL_AUTOMOUNTED=false	# 

PACKAGE_DMG_MOUNT=''					# mount point for dmg packages (only while in use)
PACKAGE_DMG_FILE=''						# path to the dmg file of dmg packages (only while in use)

OS_REV_MAJOR=''
OS_REV_MINOR=''
CPU_TYPE=''

TARGET_OS_REV=''
TARGET_OS_REV_MAJOR=''
TARGET_OS_REV_BUILD=''
TARGET_OS_NAME=''

SUPPORTING_DISKS=()
MOUNTED_DMG_MOUNT_POINTS=()

LATEST_IMAGE_MOUNT=''					# back-channel to let the mount_dmg command communicate back auto-mounts

#<!----------------------- Logging ------------------------->

# Logging levels
# Error:		always logged to everything
# Section:		CONSOLE level 1 and higher, PACKAGE level 1 and higher
# Warning:		CONSOLE level 2 and higher, PACKAGE level 1 and higher
# Information:	CONSOLE level 2 and higher, PACKAGE level 2 and higher
# Detail:		CONSOLE level 3 and higher, PACKAGE level 3 and higher
# Detail 2:		CONSOLE level 4 and higher, PACKAGE leval 4 and higher
CONSOLE_LOG_LEVEL=2
PACKAGE_LOG_LEVEL=2

# Log a message - takes up to two arguments
#	The first argument is the message to send. If blank log prints the date to the standard places for the selcted log level
#	The second argument tells the type of message. The default is information. The options are:
#		section		- header announcing that a new section is being started
#		warning		- non-fatal warning
#		error		- non-recoverable error
#		information	- general information
#		detail		- verbose detail

# everything will always be logged to the full log
# depending on the second argument and the logging levels for CONSOLE_LOG_LEVEL and PACKAGE_LOG_LEVEL the following will be logged

# Detail 2 is lines that begin with "installer:" that don't match a couple of other criteria

# commands should all have the following appended to them:
#	| (while read INPUT; do log "$INPUT " information; done)

ERROR_LOG_FORMAT="ERROR: %s\n"
SECTION_LOG_FORMAT="###### %s ######\n"
WARNING_LOG_FORMAT="WARNING: %s\n"
SUBPACKAGE_LOG_FORMAT="		%s\n"
INFORMATION_LOG_FORMAT="	%s\n"
DETAIL_LOG_FORMAT="		%s\n"

log() {
	if [ -z "$1" ] || [ "$1" == "" ] || [ "$1" == "#" ]; then
		# there is nothing to log
		return
	else
		MESSAGE=`/bin/echo "$1" | /usr/bin/awk '{gsub("installer(\[[[:digit:]]+\])*\:", ""); print $0}'`
	fi
	
	if [ -z "$2" ]; then
		LEVEL="information"
	else
		LEVEL="$2"
	fi	
	
	if [ "$LEVEL" == "error-nolog" ]; then
		/usr/bin/printf "$SECTION_LOG_FORMAT" "$MESSAGE" 1>&2
	fi
	
	if [ "$LEVEL" == "error" ]; then
		/usr/bin/printf "$SECTION_LOG_FORMAT" "$MESSAGE" | /usr/bin/tee -a "$LOG_FILE" "$PKG_LOG" 1>&2
	fi

	if [ "$LEVEL" == "section" ]; then
		TIMESTAMP=`date "+%H:%M:%S"`
		/usr/bin/printf "$TIMESTAMP $SECTION_LOG_FORMAT" "$MESSAGE" >> "$LOG_FILE"
	
		if [ $CONSOLE_LOG_LEVEL -ge 1 ]; then 
			/usr/bin/printf "$TIMESTAMP $SECTION_LOG_FORMAT" "$MESSAGE"
		fi
		if [ $PACKAGE_LOG_LEVEL -ge 1 ]; then
			/usr/bin/printf "$TIMESTAMP $SECTION_LOG_FORMAT" "$MESSAGE" >> "$PKG_LOG"
		fi
	fi
	
	if [ "$LEVEL" == "warning" ]; then
		/usr/bin/printf "$WARNING_LOG_FORMAT" "$MESSAGE" >> "$LOG_FILE"
	
		if [ $CONSOLE_LOG_LEVEL -ge 2 ]; then 
			/usr/bin/printf "$WARNING_LOG_FORMAT" "$MESSAGE"
		fi
		if [ $PACKAGE_LOG_LEVEL -ge 1 ]; then
			/usr/bin/printf "$WARNING_LOG_FORMAT" "$MESSAGE" >> "$PKG_LOG"
		fi
	fi
	
	if [ "$LEVEL" == "information" ]; then
		/usr/bin/printf "$INFORMATION_LOG_FORMAT" "$MESSAGE" >> "$LOG_FILE"
	
		if [ $CONSOLE_LOG_LEVEL -ge 2 ]; then 
			/usr/bin/printf "$INFORMATION_LOG_FORMAT" "$MESSAGE"
		fi
		if [ $PACKAGE_LOG_LEVEL -ge 2 ]; then
			/usr/bin/printf "$INFORMATION_LOG_FORMAT" "$MESSAGE" >> "$PKG_LOG"
		fi
	fi
	
	if [ "$LEVEL" == "detail" ]; then
		/usr/bin/printf "$DETAIL_LOG_FORMAT" "$MESSAGE" >> "$LOG_FILE"
		
		# here we are going to split the "detail" and "detail 2" groups
		# the different packages will also cause "informational" messages
		
		if [[ $MESSAGE == *installer:\ Installing* ]]; then
			FILTERED_MESSAGE=`/bin/echo "$MESSAGE" | /usr/bin/awk 'sub("installer: ", "")'`
		
			if [[ $MESSAGE == *base\ path* ]]; then
				if [ $CONSOLE_LOG_LEVEL -ge 3 ]; then 
					/usr/bin/printf "$SUBPACKAGE_LOG_FORMAT" "$FILTERED_MESSAGE"
				fi
				if [ $PACKAGE_LOG_LEVEL -ge 3 ]; then
					/usr/bin/printf "$SUBPACKAGE_LOG_FORMAT" "$FILTERED_MESSAGE" >> "$PKG_LOG"
				fi
			else
				if [ $CONSOLE_LOG_LEVEL -ge 2 ]; then 
					/usr/bin/printf "$SUBPACKAGE_LOG_FORMAT" "$FILTERED_MESSAGE"
				fi
				if [ $PACKAGE_LOG_LEVEL -ge 2 ]; then
					/usr/bin/printf "$SUBPACKAGE_LOG_FORMAT" "$FILTERED_MESSAGE" >> "$PKG_LOG"
				fi
			fi
		elif [[ $MESSAGE == installer:* ]]; then
		
			FILTERED_MESSAGE=`/bin/echo "$MESSAGE" | /usr/bin/awk 'sub("installer: ", "")'`
			
			if [ $CONSOLE_LOG_LEVEL -ge 4 ]; then 
				/usr/bin/printf "$DETAIL_LOG_FORMAT" "$FILTERED_MESSAGE"
			fi
			if [ $PACKAGE_LOG_LEVEL -ge 4 ]; then
				/usr/bin/printf "$DETAIL_LOG_FORMAT" "$FILTERED_MESSAGE" >> "$PKG_LOG"
			fi
		else
			if [ $CONSOLE_LOG_LEVEL -ge 3 ]; then 
				/usr/bin/printf "$DETAIL_LOG_FORMAT" "$MESSAGE"
			fi
			if [ $PACKAGE_LOG_LEVEL -ge 3 ]; then
				/usr/bin/printf "$DETAIL_LOG_FORMAT" "$MESSAGE" >> "$PKG_LOG"
			fi
		fi
	fi
}

#<!----------------------- Functions ----------------------->

bail() {	
	#If we get here theres a problem, print the usage message and then exit with a non-zero status
	usage $1
}

version() {
	# Show the version number
	/bin/echo "$PROGRAM version $VERSION"
	exit 0
}

usage() {
	# Usage format
cat <<EOF
Usage:	$PROGRAM [options]

Note:	This program must be run as root (sudo is acceptable)

Options:
	-b <folder path>	Look for the base image in this folder ($INSTALLER_FOLDER)
	-c <folder path>	Look for custom pkgs in this folder ($CUSTOM_FOLDER)
	-f			Enable non-paranoid mode (skip checking image checksumms)
	-h			Print the useage information (this) and exit
	-i <iso code>		Use <iso code> for the installer language ($ISO_CODE)
	-l <folder path>	Set the folder to use as the log folder ($LOG_FOLDER)
	-m <name>		The file name to use for the ouput file. '.dmg' will be appended as needed. ($ASR_OUPUT_FILE_NAME)
	-n <name>		The volume name to use for the output file. ($ASR_FILESYSTEM_NAME)
	-o <folder path>	Set the folder to use as the output folder ($ASR_FOLDER)
	-q			Quiet: print only errors to the console
	-r			Disable using chroot for package installs ($DISABLE_CHROOT)
	-t <folder path>	Create a scratch space in this folder ($TEMPORARY_FOLDER)
	-u <folder path>	Use folder as the BaseUpdates folder ($UPDATE_FOLDER)
	-v			Print the version number and exit
	-w <folder path>	Disk to erase and restore the new image to for testing
	-y			Enable erase-and-restore of new image to testing volume
	-z			Disable caching of the base image ($DISABLE_BASE_IMAGE_CACHING)
	
	-I <dmg path>		Use dmg at this path as the installer disk.
	-J <dmg path>		Mount dmg at this path during installs.
	-K <folder path>	Use folder as a source for updates, call multiple time in order for multiple folders.
EOF
	if [ -z $1 ]; then
		exit 1;
	else
		exit $1
	fi
}

mount_dmg() {
	# input
	#	$1 - path to file (manditory)
	#	$2 - mount point (optional)
	#	$3 - mount name (optional)
	#	$4 - mount options (optional)
	
	set +o nounset
	
	LATEST_IMAGE_MOUNT=''
	
	if [ -z "$1" ]; then
		log "Internal error: mount_dmg called without a source file" error
	fi
	if [ ! -f "$1" ]; then
		log "Internal error: mount_dmg called with invalid source file: $1" error
	fi
	
	# Get the absolute path to the image
	DMG_PATH=$( cd $( dirname "$1" ); echo "`pwd`/`basename "$1"`" )
	
	# Test to see if the image is already mounted
	IFS=$'\n'
	MOUNTED_IMAGES=`/usr/bin/hdiutil info -plist | /usr/bin/awk '/<key>image-path<\/key>/ { getline; gsub(/[[:space:]]*\<\/?string>/,""); print }'`
	IMAGE_MOUNT_POINTS=`/usr/bin/hdiutil info -plist | /usr/bin/awk '/<key>mount-point<\/key>/ { getline; gsub(/[[:space:]]*\<\/?string>/,""); print }'`
	# convert to arrays
	MOUNTED_IMAGES=( $MOUNTED_IMAGES )
	IMAGE_MOUNT_POINTS=( $IMAGE_MOUNT_POINTS )
	
	for (( mountCounter = 0 ; mountCounter < ${#MOUNTED_IMAGES[@]} ; mountCounter++ )); do
		if [ "$MOUNTED_IMAGES[$mountCounter]" == "$DMG_PATH" ]; then
			# The image is already mounted
			log "Disk image $DMG_PATH was already mounted at $TEMP_MOUNT_POINT" detail
			LATEST_IMAGE_MOUNT=$IMAGE_MOUNT_POINTS[$mountCounter]
			return 1
		fi
	done
	
	# We now know it is not currently mounted
	
	# If there was no mount point given, make a new one
	if [ -z "$2" ]; then
		# Create a new mount point in the shield directory
		TEMP_MOUNT_POINT=`/usr/bin/mktemp -d "$HOST_MOUNT_FOLDER/$MOUNT_POINT_TEMPLATE"`
	else
		TEMP_MOUNT_POINT="$2"
	fi
	
	# Test the mount point
	if [ ! -d "$TEMP_MOUNT_POINT" ]; then
		log "Internal error: mount_dmg called with invalid mount point: $TEMP_MOUNT_POINT" error
	fi
	
	# Log the mount attempt
	if [ -z $3 ]; then
		log "Mounting disk image from $DMG_PATH at $TEMP_MOUNT_POINT" detail
	else
		log "Mounting $3 ($DMG_PATH) at $TEMP_MOUNT_POINT" detail
	fi
	
	# Mount the image
	if [ $ENABLE_NON_PARANOID_MODE == true ]; then
		/usr/bin/hdiutil mount "$DMG_PATH" -nobrowse -noautofsck -noverify $4 -puppetstrings -owners on -mountpoint "$TEMP_MOUNT_POINT" 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
	else
		/usr/bin/hdiutil mount "$DMG_PATH" -nobrowse $4 -puppetstrings -owners on -mountpoint "$TEMP_MOUNT_POINT" 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
	fi
	
	# Add the disk to the list of mount points
	MOUNTED_DMG_MOUNT_POINTS[${#MOUNTED_DMG_MOUNT_POINTS[@]}]="$TEMP_MOUNT_POINT"
	
	set -o nounset
	
	LATEST_IMAGE_MOUNT="$TEMP_MOUNT_POINT"
	return 0
}

unmount_dmg() {
	set +o nounset
	
	if [ -z "$1" ]; then
		log "Internal error: tried to eject an image without a path" error
		return 1
	fi
	if [ ! -d "$1" ]; then
		log "Internal error: tried to eject and image from $1 but that path is not a directory" error
		return 1
	fi
	
	
	# ToDo: check to see that there is an image mounted here
	
	FEEDBACK=`/usr/bin/hdiutil eject "$1" 2>&1`
	if [ ${?} -ne 0 ]; then
		echo "$FEEBACK" | (while read INPUT; do log "$INPUT " detail; done)
		# for some reason it did not un-mount, so we will try again with more force
		log "The image did not eject cleanly, so I will force it" information
		FEEDBACK=`/usr/bin/hdiutil eject -force "$1" 2>&1`
		if [ ${?} -ne 0 ]; then
			echo "$FEEDBACK" | (while read INPUT; do log "$INPUT " detail; done)
			log "Failed to unmount the $2 image from $1, unable to continue" error
			return 1
		else
			echo "$FEEDBACK" | (while read INPUT; do log "$INPUT " detail; done)
		fi
	else
		echo "$FEEBACK" | (while read INPUT; do log "$INPUT " detail; done)
	fi
	
	# Remove the disk from MOUNTED_DMG_MOUNT_POINTS 
	for (( unmountDiskCount = 0 ; unmountDiskCount < ${#MOUNTED_DMG_MOUNT_POINTS[@]} ; unmountDiskCount++ )); do
		if [ ! -z "${MOUNTED_DMG_MOUNT_POINTS[$unmountDiskCount]}" ] && [ "${MOUNTED_DMG_MOUNT_POINTS[$unmountDiskCount]}" == "$1" ]; then
			unset MOUNTED_DMG_MOUNT_POINTS[$unmountDiskCount]
		fi
	done
	
	if [ -z "$2" ]; then
		log "Unmounted image from $1" detail
	else
		log "Unmounted the $2 image from $1" detail
	fi
	
	set -o nounset
}

#<!------------------------ Phases ------------------------->

check_setup () {
	IFS=$'\n'
	
	# Check the language
	LANGUAGE_CODE_IS_VALID=false
	for LANGUAGE_CODE in $(/usr/sbin/installer -listiso | /usr/bin/tr "\t" "\n"); do
		if [ "$ISO_CODE" == "$LANGUAGE_CODE" ]; then
			LANGUAGE_CODE_IS_VALID=true
		fi
	done
	if [ $LANGUAGE_CODE_IS_VALID == false ]; then
		log "The ISO language code $ISO_CODE is not recognized by the Apple installer" error
		exit 1
	fi
	
	# If the ASR_OUPUT_FILE_NAME does not end in .dmg, add it
	if [ "`/bin/echo $ASR_OUPUT_FILE_NAME | /usr/bin/awk 'tolower($1) ~ /.*\.dmg$/ { print "true" }'`" != "true" ]; then
		ASR_OUPUT_FILE_NAME="$ASR_OUPUT_FILE_NAME.dmg"
	fi
	
	# make sure that the CONSOLE_LOG_LEVEL is one of the accepted values
	if [ "$CONSOLE_LOG_LEVEL" != "0" ] && [ "$CONSOLE_LOG_LEVEL" != "1" ] && [ "$CONSOLE_LOG_LEVEL" != "2" ] && [ "$CONSOLE_LOG_LEVEL" != "3" ] && [ "$CONSOLE_LOG_LEVEL" != "4" ]; then
		log "The conole log level must be an integer between 0 and 4" error
	fi
}

# check to make sure we are root
rootcheck() {
	# Root is required to run instadmg
	if [ $EUID != 0 ]; then
		log "You must run this utility using sudo or as root!" error-nolog
		exit 1
	fi
}

startup() {	
	IFS=' '
	
	FOLDER_LIST="UPDATE_FOLDER CUSTOM_FOLDER ASR_FOLDER BASE_IMAGE_CACHE LOG_FOLDER TEMPORARY_FOLDER"
	
	if [ -z "$INSTALLER_DISK" ]; then
		# We need to check the INSTALLER_FOLDER
		FOLDER_LIST="$FOLDER_LIST INSTALLER_FOLDER"
	fi
	
	
	for FOLDER_ITEM in $FOLDER_LIST; do
		# sanitise the folder paths to make sure that they don't end in /
		if [ ${!FOLDER_ITEM: -1} == '/' ] && [ "${!FOLDER_ITEM}" != '/' ]; then
			THE_STR="${!FOLDER_ITEM}"
			eval $FOLDER_ITEM='${THE_STR: 0: $((${#THE_STR} - 1)) }'
		fi
		# check that all the things that should be folders are folders
		if [ ! -d "${!FOLDER_ITEM}" ]; then
			log "A required folder is missing or was not a folder: $FOLDER_ITEM: ${!FOLDER_ITEM}" error
			exit 1
		fi
	done
	
	# Create folder to enclose host mount points
	
	HOST_MOUNT_FOLDER=`/usr/bin/mktemp -d "$TEMPORARY_FOLDER/$MOUNT_FOLDER_TEMPLATE"`
	/bin/chmod og+x "$HOST_MOUNT_FOLDER" 2>&1 | (while read INPUT; do log "$INPUT " detail; done) # allow the installer user thourgh
	log "Host mount folder: $HOST_MOUNT_FOLDER" detail
	
	# Get the MacOS X version information.
	OS_REV_MAJOR=`/usr/bin/sw_vers -productVersion | awk -F "." '{ print $2 }'`
	OS_REV_MINOR=`/usr/bin/sw_vers -productVersion | awk -F "." '{ print $3 }'`
	CPU_TYPE=`/usr/bin/arch`
}

# Look for the baseOS disk and supporting disks (if not provided)
find_base_os() {
	log "Finding main MacOS X installer disk" section
	
	if [ -z "$INSTALLER_DISK" ]; then
		# use the old folder searching method
		
		if [ !-z "$SUPPORTING_DISKS" ]; then
			log "If the -J flag is used, then the -I flag must also be used" error
			exit 1
		fi
				
		IFS=$'\n'
		for IMAGE_FILE in $(/usr/bin/find "$INSTALLER_FOLDER" -iname '*.dmg'); do
			FOUND_IMAGE_FILE=false
			for (( namesCount = 0 ; namesCount < ${#ALLOWED_INSTALLER_DISK_NAMES[@]} ; namesCount++ )); do
				if [ "$IMAGE_FILE" == "$INSTALLER_FOLDER/${ALLOWED_INSTALLER_DISK_NAMES[$namesCount]}" ]; then
					CURRENT_OS_INSTALL_FILE="$INSTALLER_FOLDER/$IMAGE_FILE"
					log "Found primary OS installer disk: $CURRENT_OS_INSTALL_FILE" information
					FOUND_IMAGE_FILE=true
					break
				fi
			done
			
			if [ $FOUND_IMAGE_FILE == false ]; then
				# if it is not a primary disk, it must be a supporting one
				SUPPORTING_DISKS[${#SUPPORTING_DISKS[*]}]="$INSTALLER_FOLDER/$IMAGE_FILE"
			fi
		done
	else
		# user should have suplpied us with everything we need
		
		# Check for the disk at the path supplied
		if [ -f "$INSTALLER_DISK" ]; then
			CURRENT_OS_INSTALL_FILE="$INSTALLER_DISK"
		else
			log "Unable to find installer disk at supplied path: $INSTALLER_DISK" error
			exit 1
		fi
	fi
		
	if [ -z "$CURRENT_OS_INSTALL_FILE" ]; then
		log "Unable to find primary installer disk" error
		exit 1
	fi
	
	log "Found the image at: $CURRENT_OS_INSTALL_FILE" information
}

# Look for and mount a cached image
mount_cached_image() {
	log "Looking for a Cached Image" section
	
	# figure out the name the filesystem should have
	
	# compatibility for old-style checksums (using colons)
	OLD_STYLE_TARGET_IMAGE_CHECKSUM=''	# using colons
	
	TARGET_IMAGE_CHECKSUM=`/usr/bin/hdiutil imageinfo "$CURRENT_OS_INSTALL_FILE" | /usr/bin/awk '/^Checksum Value:/ { print $3 }' | /usr/bin/sed 's/\\$//'`
	
	# sanity check
	if [ -z "$TARGET_IMAGE_CHECKSUM" ]; then
		log "Unable to get checksum for image: $CURRENT_OS_INSTALL_FILE" error
		exit 1
	fi
	
	INSTALLER_CHOICES_FILE=''
	if [ $OS_REV_MAJOR -gt 4 ] && [ -e "$INSTALLER_FOLDER/InstallerChoices.xml" ]; then
		INSTALLER_CHOICES_FILE="$INSTALLER_FOLDER/InstallerChoices.xml"
		
		INSTALLER_CHOICES_CHEKSUM=`/usr/bin/openssl dgst -sha1 "$INSTALLER_CHOICES_FILE" | awk 'sub(".*= ", "")'`
		OLD_STYLE_TARGET_IMAGE_CHECKSUM="${TARGET_IMAGE_CHECKSUM}:${INSTALLER_CHOICES_CHEKSUM}"
		TARGET_IMAGE_CHECKSUM="${TARGET_IMAGE_CHECKSUM}_${INSTALLER_CHOICES_CHEKSUM}"
	fi
	
	# look for the cached image, new style first
	if [ -e "${BASE_IMAGE_CACHE}/${TARGET_IMAGE_CHECKSUM}.dmg" ]; then
		TARGET_IMAGE_FILE="${BASE_IMAGE_CACHE}/${TARGET_IMAGE_CHECKSUM}.dmg"
	
	elif [ -e "${BASE_IMAGE_CACHE}/${OLD_STYLE_TARGET_IMAGE_CHECKSUM}.dmg" ]; then
		TARGET_IMAGE_FILE="${BASE_IMAGE_CACHE}/${OLD_STYLE_TARGET_IMAGE_CHECKSUM}.dmg"
	else
		log "No cached image found" information
		return
	fi
	
	# Create mount point for the (read-only) target
	TARGET_IMAGE_MOUNT=`/usr/bin/mktemp -d "$HOST_MOUNT_FOLDER/$MOUNT_POINT_TEMPLATE"`
	/bin/chmod og+x "$TARGET_IMAGE_MOUNT" 2>&1 | (while read INPUT; do log "$INPUT " detail; done) # allow the installer user thourgh
	log "Current image mount point: $TARGET_IMAGE_MOUNT" detail
	
	# Decide the location for the shadow file to be attached to the target dmg
	SHADOW_FILE_LOCATION="$HOST_MOUNT_FOLDER/`/usr/bin/uuidgen`.shadowfile"
	log "Shadow file location: $SHADOW_FILE_LOCATION" detail
	
	# Mount the image and the shadow file
	log "Mounting the shadow file ($SHADOW_FILE_LOCATION) onto the cached image ($TARGET_IMAGE_FILE)" information
	if [ $ENABLE_NON_PARANOID_MODE == true ]; then
		/usr/bin/hdiutil mount "$TARGET_IMAGE_FILE" -nobrowse -noautofsck -noverify -puppetstrings -owners on -mountpoint "$TARGET_IMAGE_MOUNT" -shadow "$SHADOW_FILE_LOCATION" | (while read INPUT; do log "$INPUT " detail; done)
	else
		/usr/bin/hdiutil mount "$TARGET_IMAGE_FILE" -nobrowse -puppetstrings -owners on -mountpoint "$TARGET_IMAGE_MOUNT" -shadow "$SHADOW_FILE_LOCATION" | (while read INPUT; do log "$INPUT " detail; done)
	fi
	
	# Check that the host OS is the same dot version as the target, or newer
	TARGET_OS_REV=`/usr/bin/defaults read "$TARGET_IMAGE_MOUNT/System/Library/CoreServices/SystemVersion" ProductVersion`
	TARGET_OS_REV_MAJOR=`/usr/bin/defaults read "$TARGET_IMAGE_MOUNT/System/Library/CoreServices/SystemVersion" ProductVersion | awk -F "." '{ print $2 }'`
	TARGET_OS_REV_BUILD=`/usr/bin/defaults read "$TARGET_IMAGE_MOUNT/System/Library/CoreServices/SystemVersion" ProductBuildVersion`
	TARGET_OS_NAME=`/usr/bin/defaults read "$TARGET_IMAGE_MOUNT/System/Library/CoreServices/SystemVersion" ProductName`
	if [ $OS_REV_MAJOR -lt $TARGET_OS_REV_MAJOR ]; then
		# we can't install a newer os from an older os
		log "Trying to install a newer os ($TARGET_OS_REV_MAJOR) while running on an older os ($OS_REV_MAJOR), this is not possible" error
		exit 1
	fi
	
	# TODO: check to see if there was a problem
}

# Mount the OS source image and any supporting disks
mount_os_install() {
	log "Mounting Mac OS X installer image" section
	
	mount_dmg "$CURRENT_OS_INSTALL_FILE"
	if [ $? -ne 0 ]; then
		log "Unable to mount the Instal Disc: $CURRENT_OS_INSTALL_FILE" error
		exit 1
	fi
	
	CURRENT_OS_INSTALL_MOUNT=$LATEST_IMAGE_MOUNT
		
	# check to make sure we are leaving something useful
	if [ -z "$CURRENT_OS_INSTALL_MOUNT" ]; then
		log "No OS install disk or cached build was found" error
		exit 1
	fi
	
	# Check that the host OS is the same dot version as the target, or newer
	TARGET_OS_REV=`/usr/bin/defaults read "$CURRENT_OS_INSTALL_MOUNT/System/Library/CoreServices/SystemVersion" ProductVersion`
	TARGET_OS_REV_MAJOR=`/usr/bin/defaults read "$CURRENT_OS_INSTALL_MOUNT/System/Library/CoreServices/SystemVersion" ProductVersion | awk -F "." '{ print $2 }'`
	TARGET_OS_REV_BUILD=`/usr/bin/defaults read "$TARGET_IMAGE_MOUNT/System/Library/CoreServices/SystemVersion" ProductBuildVersion`
	TARGET_OS_NAME=`/usr/bin/defaults read "$TARGET_IMAGE_MOUNT/System/Library/CoreServices/SystemVersion" ProductName`
	if [ $OS_REV_MAJOR -lt $TARGET_OS_REV_MAJOR ]; then
		# we can't install a newer os from an older os
		log "Trying to install a newer os ($TARGET_OS_REV_MAJOR) while running on an older os ($OS_REV_MAJOR), this does not work" error
		exit 1
	fi
	
	log "Mac OS X installer image mounted" information
	
	if [ ${#SUPPORTING_DISKS[@]} -gt 0 ]; then
		log "Mounting supporting disks" section
		for (( diskCount = 0 ; diskCount < ${#SUPPORTING_DISKS[@]} ; diskCount++ )); do
			mount_dmg "${SUPPORTING_DISKS[$diskCount]}"
			log "Mounted supporting disk ${SUPPORTING_DISKS[$diskCount]} at $LATEST_IMAGE_MOUNT" information
		done
	fi
}

# setup and create the DMG.
create_and_mount_image() {
	log "Creating intermediary disk image" section
	
	if [ "$CPU_TYPE" == "ppc" ]; then
		LAYOUT_TYPE="SPUD"
	elif [ "$CPU_TYPE" == "i386" ]; then
		LAYOUT_TYPE="GPTSPUD"
	else
		log "Unknown CPU type: $CPU_TYPE. Unable to continue" error
		exit 1
	fi
	
	# Create mount point for the (read-only) target
	TARGET_IMAGE_MOUNT=`/usr/bin/mktemp -d "/tmp/$MOUNT_POINT_TEMPLATE"` # note: we do not use the temp folder, as it blows up
	/bin/chmod og+x "$TARGET_IMAGE_MOUNT" 2>&1 | (while read INPUT; do log "$INPUT " detail; done) # allow the installer user thourgh
	log "Current image mount point: $TARGET_IMAGE_MOUNT" detail
	
	# Decide the location for the shadow file to be attached to the target dmg
	SHADOW_FILE_LOCATION="$HOST_MOUNT_FOLDER/`/usr/bin/uuidgen`"
	log "Shadow file location: $SHADOW_FILE_LOCATION.sparseimage" detail
	
	/usr/bin/hdiutil create -size $DMG_SIZE -volname "$ASR_FILESYSTEM_NAME" -layout "$LAYOUT_TYPE" -type SPARSE -fs "HFS+" "$SHADOW_FILE_LOCATION" | (while read INPUT; do log "$INPUT " detail; done)
	if [ $? -ne 0 ]; then
		log "Failed to create targetimage: $SHADOW_FILE_LOCATION" error
		exit 1
	fi
	
	# The create command appends a ".sparseimage" to what we give it
	SHADOW_FILE_LOCATION="$SHADOW_FILE_LOCATION.sparseimage"
	
	/usr/bin/hdiutil mount "$SHADOW_FILE_LOCATION" -owners on -readwrite -noverify -nobrowse -mountpoint "$TARGET_IMAGE_MOUNT" | (while read INPUT; do log "$INPUT " detail; done)
	if [ $? -ne 0 ]; then
		log "Failed to mount target image: $SHADOW_FILE_LOCATION at: $TARGET_IMAGE_MOUNT" error
		exit 1
	fi
	
	log "Target image: $SHADOW_FILE_LOCATION mounted sucessfuly at: $TARGET_IMAGE_MOUNT" information
}

# Install from installation media to the DMG
install_system() {
	log "Beginning Installation from $CURRENT_OS_INSTALL_MOUNT" section
	
	INSTALLER_CHOICES_FILE=''
	
	# Check for InstallerChoices file, note we are excluding < 10.5
	if [ $OS_REV_MAJOR -gt 4 ]; then
		if [ -e "$INSTALLER_FOLDER/InstallerChoices.xml" ]; then
			INSTALLER_CHOICES_FILE="$INSTALLER_FOLDER/InstallerChoices.xml"
		fi
	else
		log "Running on Pre-10.5. InstallerChoices.xml files do not work" information
	fi
	
	OS_INSTALLER_PACKAGE=''
	if [ -e "$CURRENT_OS_INSTALL_MOUNT/System/Installation/Packages/OSInstall.mpkg" ]; then
		OS_INSTALLER_PACKAGE="$CURRENT_OS_INSTALL_MOUNT/System/Installation/Packages/OSInstall.mpkg"
	else
		log "The OS Install File is missing the OS Installer Package!" error
		exit 1
	fi
	
	# Fix a bug in 'installer' on certian versions of the OS
	/bin/mkdir -p "$TARGET_IMAGE_MOUNT/Library/Caches"
	
	if [ -z "$INSTALLER_CHOICES_FILE" ]; then
		log "Installing system from: $CURRENT_OS_INSTALL_MOUNT onto image at: $TARGET_IMAGE_MOUNT using language code: $ISO_CODE" information
		/usr/sbin/installer -verboseR -dumplog -pkg "$OS_INSTALLER_PACKAGE" -target "$TARGET_IMAGE_MOUNT" -lang $ISO_CODE 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
	else
		log "Installing system from: $CURRENT_OS_INSTALL_MOUNT onto image at: $TARGET_IMAGE_MOUNT using InstallerChoices file: $INSTALLER_CHOICES_FILE and language code: $ISO_CODE" information
		/usr/sbin/installer -verboseR -dumplog -applyChoiceChangesXML "$INSTALLER_CHOICES_FILE" -pkg "$OS_INSTALLER_PACKAGE" -target "$TARGET_IMAGE_MOUNT" -lang "$ISO_CODE" 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
	fi

	if [ $? -ne 0 ]; then
		log "Failed to install the base image" error
		exit 1
	fi
	
	# Eject the installer disk
	if [ $CURRENT_OS_INSTALL_AUTOMOUNTED == true ]; then
		unmount_dmg "$CURRENT_OS_INSTALL_MOUNT" "Primary OS install disk"
		/bin/rmdir "$CURRENT_OS_INSTALL_MOUNT" 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
	fi
	CURRENT_OS_INSTALL_MOUNT=''
	# TODO: unmount supporting disks
	
	log "Base OS installed" information
}

save_cached_image()	{
	# if we are at this point we need to close the image, move it to the cached folder
	log "Compacting and saving cached image to: $BASE_IMAGE_CACHE/$TARGET_IMAGE_CHECKSUM.dmg" information
	
	# unmount the image
	unmount_dmg "$TARGET_IMAGE_MOUNT" "target image" || exit 1
	
	# move the image to the cached folder with the appropriate name
	TARGET_IMAGE_FILE="$BASE_IMAGE_CACHE/$TARGET_IMAGE_CHECKSUM.dmg"
	/bin/mv "$SHADOW_FILE_LOCATION" "$TARGET_IMAGE_FILE"
	if [ $? -ne 0 ]; then
		log "Unable to move the image to cache folder, unable to continue" error
		exit 1
	fi
	
	# NOTE: backing off this code for the moment... does not seem happy
	# compress the image and store it in the new location
	#/usr/bin/hdiutil convert -format UDZO -imagekey zlib-level=6 -o "$TARGET_IMAGE_FILE" "$SHADOW_FILE_LOCATION" | (while read INPUT; do log "$INPUT " detail; done)
	
	# set the appropriate metadata on the file so that time-machine does not back it up
	if [ -x /usr/bin/xattr ]; then
		/usr/bin/xattr -w com.apple.metadata:com_apple_backup_excludeItem com.apple.backupd "$TARGET_IMAGE_FILE"
	fi
}

# make any adjustments that need to be made before installing packages
prepare_image() {
	if [ $DISABLE_CHROOT == false ]; then
		# create a folder inside the chroot with the same path as the mount point pointing at root to fix some installer bugs
		/bin/mkdir -p "${TARGET_IMAGE_MOUNT}${TARGET_IMAGE_MOUNT}" 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
		/bin/rmdir "${TARGET_IMAGE_MOUNT}${TARGET_IMAGE_MOUNT}" 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
		/bin/ln -s / "${TARGET_IMAGE_MOUNT}${TARGET_IMAGE_MOUNT}" 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
		
		# make sure that the temp folder exists inside the image
		TARGET_TEMP_FOLDER="${TARGET_IMAGE_MOUNT}/private/tmp"
		/bin/mkdir -p "$TARGET_TEMP_FOLDER" 2>&1 | (while read INPUT; do log "$INPUT " detail; done) # this should probably already exist
	fi
}

# install packages from a folder of folders (01, 02, 03...etc)
install_packages_from_folder() {
	SELECTED_FOLDER="$1"
	
	log "Beginning Update Installs from $SELECTED_FOLDER" section

	if [ -z "$SELECTED_FOLDER" ]; then
		log "install_packages_from_folder called without folder" error
		exit 1;
	fi
	
	IFS=$'\n'
	for ORDERED_FOLDER in $(/bin/ls -A1 "$SELECTED_FOLDER" | /usr/bin/awk "/^[[:digit:]]+.*$/" | /usr/bin/sort -n); do
		TARGET="$SELECTED_FOLDER/$ORDERED_FOLDER"
		ORIGINAL_TARGET="$TARGET"
		CHROOT_TARGET=''
		TARGET_COPIED=false
		
		PACKAGE_DMG_MOUNT=''
		PACKAGE_DMG_FILE=''
		
		log "Working on folder $ORDERED_FOLDER (`date '+%H:%M:%S'`)" information
				
		# first resolve any chain of symlinks
		while [ -h "$TARGET" ]; do
			# look into this being a dmg
			NEW_LINK=`/usr/bin/readlink "$TARGET"`
			BASE_LINK=`/usr/bin/dirname "$TARGET"`
			TARGET="$BASE_LINK/$NEW_LINK"
		done
		
		# check for dmgs
		if [ -f "$TARGET" ]; then
			# see if it is a dmg. If it does not have a name, we can trust it is not a dmg
			DMG_INTERNAL_NAME=`/usr/bin/hdiutil imageinfo "$TARGET" 2>/dev/null | awk '/^\tName:/ && sub("\tName: ", "")'`
			if [ -z "$DMG_INTERNAL_NAME" ]; then
				# this is an unknown file type, so we need to bail
				log "Error: $ORIGINAL_TARGET pointed at $TARGET, which is an unknown file type (should be a dmg or a folder)" error
				exit 1
			else
				PACKAGE_DMG_FILE="$TARGET"
				
				# mount in the host mount folder
				TARGET=`/usr/bin/mktemp -d "$HOST_MOUNT_FOLDER/$MOUNT_POINT_TEMPLATE"`
				/bin/chmod og+x "$TARGET" 2>&1 | (while read INPUT; do log "$INPUT " detail; done) # allow the installer user thourgh
				PACKAGE_DMG_MOUNT="$TARGET"
				log "	Mounting the package dmg: $DMG_INTERNAL_NAME ($ORIGINAL_TARGET) at: $TARGET" information
				mount_dmg "$PACKAGE_DMG_FILE" "$TARGET"
			fi
		fi
		
		# If we are using a chroot jail copy the contents of the folder into the image
		if [ $DISABLE_CHROOT == false ]; then
			# create a folder inside /tmp on the target
			
			CHROOT_TARGET=`cd "$TARGET_IMAGE_MOUNT"; /usr/bin/mktemp -d "private/tmp/$SOURCE_FOLDER_TEMPLATE"`
			/bin/chmod og+x "$TARGET_IMAGE_MOUNT/$CHROOT_TARGET"
			CHROOT_TARGET="/$CHROOT_TARGET"
			
			log "	Copying folder $TARGET into the target at $CHROOT_TARGET" information
			/bin/cp -RHL "$TARGET/" "${TARGET_IMAGE_MOUNT}${CHROOT_TARGET}/" 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
			
			TARGET_COPIED=true
		fi
		
		ABSOLUTE_TARGET_PATH=( `cd "$TARGET"; pwd -P` )
		
		IFS=$'\n'
		FOUND_PACKAGE=false
		for UPDATE_PKG in $(/usr/bin/find -L "$ABSOLUTE_TARGET_PATH" -maxdepth 1 -iname '*pkg' | /usr/bin/awk 'tolower() ~ /\.(m)?pkg/ && !/\/\._/'); do
			FOUND_PACKAGE=true
			CHOICES_FILE=''
			PACKAGE_DISABLE_CHROOT=false
			
			# check to see if this package should be excluded from the chroot system
			if [ -d "$UPDATE_PKG" ]; then
				# does not work on flat packages
				
				PACKAGE_BUNDLE_ID=`/usr/bin/defaults read "$UPDATE_PKG/Contents/Info" "CFBundleIdentifier" 2>/dev/null`
				PACKAGE_CHROOT_DISABLE=`/usr/bin/defaults read "$UPDATE_PKG/Contents/Info" "InstaDMG Chroot Disable" 2>/dev/null`

				if [ ! -z "$PACKAGE_CHROOT_DISABLE" ]; then
					PACKAGE_DISABLE_CHROOT=true
				fi
				
				if [ ! -z "$PACKAGE_BUNDLE_ID" ]; then
					BUNDLE_ID_ARRAY_LENGTH=${#CHROOT_EXCLUDED_CODES[@]}
					INDEX=0
					while [ "$INDEX" -lt "$BUNDLE_ID_ARRAY_LENGTH" ]; do
						if [ "$PACKAGE_BUNDLE_ID" == "${CHROOT_EXCLUDED_CODES[$INDEX]}" ]; then
							PACKAGE_DISABLE_CHROOT=true
						fi
						let "INDEX = $INDEX + 1"
					done
				fi
				
			fi
						
			if [ -e "$TARGET/InstallerChoices.xml" ] && [ $OS_REV_MAJOR -ge 5 ]; then # remember: 10.4 and before can't use InstallerChoices files
				CHOICES_FILE="InstallerChoices.xml"
				# TODO: better handle multiple pkg's and InstallerChoice files named for the file they should handle
			fi		
			
			TARGET_FILE_NAME=`/usr/bin/basename "$UPDATE_PKG"`
			if [ "$ORIGINAL_TARGET" == "$TARGET" ]; then
				CONTAINER_PATH="$TARGET"
			else
				# probably a dmg installer
				CONTAINER_PATH=`/usr/bin/readlink "$ORIGINAL_TARGET"`
			fi
			
			if [ -z "$CHOICES_FILE" ]; then
				if [ $DISABLE_CHROOT == false ] && [ $PACKAGE_DISABLE_CHROOT == false ]; then
					log "	Installing $TARGET_FILE_NAME from ${CONTAINER_PATH} (${ORDERED_FOLDER}) inside a chroot jail" information
					
					( cd "$TARGET_IMAGE_MOUNT"; /usr/sbin/chroot . /usr/sbin/installer -verboseR -dumplog -pkg "$CHROOT_TARGET/$TARGET_FILE_NAME" -target / ) 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
				else
					log "	Installing $TARGET_FILE_NAME from ${CONTAINER_PATH} (${ORDERED_FOLDER})" information
					/usr/sbin/installer -verboseR -dumplog -pkg "$TARGET/$TARGET_FILE_NAME" -target "$TARGET_IMAGE_MOUNT" 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
				fi
			else
				if [ $DISABLE_CHROOT == false ] && [ $PACKAGE_DISABLE_CHROOT == false ]; then
					log "	Installing $TARGET_FILE_NAME from ${CONTAINER_PATH} (${ORDERED_FOLDER}) with XML Choices file: $CHOICES_FILE inside a chroot jail" information
					
					( cd "$TARGET_IMAGE_MOUNT"; /usr/sbin/chroot . /usr/sbin/installer -verboseR -dumplog -applyChoiceChangesXML "/private/tmp/$CHOICES_FILE" -pkg "$CHROOT_TARGET/$TARGET_FILE_NAME" -target / ) 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
				else
					log "	Installing $TARGET_FILE_NAME from ${CONTAINER_PATH} (${ORDERED_FOLDER}) with XML Choices file: $CHOICES_FILE" information
					/usr/sbin/installer -verboseR -dumplog -applyChoiceChangesXML "$TARGET/$CHOICES_FILE" -pkg "$TARGET/$TARGET_FILE_NAME" -target "$TARGET_IMAGE_MOUNT" 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
				fi
			fi
		done
		
		# if there was no package here, look for a single naked .app
		if [ $FOUND_PACKAGE == false ]; then
			
			COPY_SOURCE=""
			
			if [ $DISABLE_CHROOT == false ]; then
				if [ 1 -eq `/bin/ls "$CHROOT_TARGET" | grep -c ".app$"` ]; then
					COPY_SOURCE=`/bin/ls "$CHROOT_TARGET" | grep ".app$"`
				fi
			else
				if [ 1 -eq `/bin/ls "$TARGET" | grep -c ".app$"` ]; then
					COPY_SOURCE=`/bin/ls "$TARGET" | grep ".app$"`
				fi
			fi
			
			if [ ! -z $COPY_SOURCE ]; then
				FOUND_PACKAGE=true
			
				log "Copying $COPY_SOURCE to the Applications folder on $TARGET_IMAGE_MOUNT" detail
				/bin/cp -R "$TARGET/$COPY_SOURCE" "$TARGET_IMAGE_MOUNT/Applications" 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
				
				# Wipe the quarentine property away
				/usr/bin/xattr -d -r "com.apple.quarantine" "$TARGET_IMAGE_MOUNT/Applications/$COPY_SOURCE" 2>/dev/null 1>/dev/null
			fi
		fi
		
		# if there was still nothing found, then report it
		if [ $FOUND_PACKAGE == false ]; then
			log "Nothing found to install in $ORIGINAL_TARGET (${ORDERED_FOLDER})" error
		fi
		
		# cleanup
		if [ ! -z "$PACKAGE_DMG_MOUNT" ]; then
			unmount_dmg "$PACKAGE_DMG_MOUNT" "Package DMG"
			# remove up the mount point
			/bin/rmdir "$PACKAGE_DMG_MOUNT" 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
			PACKAGE_DMG_MOUNT=''
		fi
			
		if [ $TARGET_COPIED == true ]; then
			# delete the copied folder
			log "Removing the copied folder: ${TARGET_IMAGE_MOUNT}${CHROOT_TARGET}" detail
			/bin/rm -Rf "${TARGET_IMAGE_MOUNT}${CHROOT_TARGET}" 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
		fi
		
		log "Folder $ORDERED_FOLDER done (`date '+%H:%M:%S'`)" information
	done
}

# clean up some generic installer mistakes
clean_up_image() {
	log "Correcting some generic installer errors" section
	
	# find all the symlinks that are pointing to $TARGET_IMAGE_MOUNT, and make them point at the "root"
	log "Correcting symlinks that point off the disk" information
	IFS=$'\n'
	for THIS_LINK in $(/usr/bin/find -x "$TARGET_IMAGE_MOUNT" -type l); do
		if [ `/usr/bin/readlink "$THIS_LINK" | /usr/bin/grep -c "$TARGET_IMAGE_MOUNT"` -gt 0 ]; then
		
			log "Correcting soft-link: $THIS_LINK" detail
			CORRECTED_LINK=`/usr/bin/readlink "$THIS_LINK" | /usr/bin/awk "sub(\"$TARGET_IMAGE_MOUNT\", \"\") { print }"`
			
			/bin/rm "$THIS_LINK"
			/bin/ln -fs "$CORRECTED_LINK" "$THIS_LINK" | (while read INPUT; do log "$INPUT " detail; done)
		
		fi
	done
	
	# Close any open files on the target
	log "Closing programs that have opened files on the disk" information
	/usr/sbin/lsof | /usr/bin/grep "$TARGET_IMAGE_MOUNT/" | /usr/bin/awk '{ print $2 }' | /usr/bin/sort -u | /usr/bin/xargs /bin/kill 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
	
	# Delete Extensions.mkext
	log "Deleting Extensions.mkext cache file" information
	/bin/rm -vf "$TARGET_IMAGE_MOUNT/System/Library/Extensions.mkext" | (while read INPUT; do log "$INPUT " detail; done)
	
	# Delete items from caches and temps
	log "Deleting cache files created during installations" information
	/bin/rm -vRf "$TARGET_IMAGE_MOUNT/System/Library/Caches/*" | (while read INPUT; do log "$INPUT " detail; done)
	/bin/rm -vRf "$TARGET_IMAGE_MOUNT/Library/Caches/*" | (while read INPUT; do log "$INPUT " detail; done)
	/bin/rm -vRf "$TARGET_IMAGE_MOUNT/private/var/folders/*" | (while read INPUT; do log "$INPUT " detail; done)
	/bin/rm -vRf "$TARGET_IMAGE_MOUNT/private/var/tmp/*" | (while read INPUT; do log "$INPUT " detail; done)
	/bin/rm -vRf "$TARGET_IMAGE_MOUNT/private/tmp/*" | (while read INPUT; do log "$INPUT " detail; done)

}

# close up the DMG, compress and scan for restore
close_up_and_compress() {
	log "Creating the deployment DMG and scanning for ASR" section
	
	# We'll rename the newly installed system so that computers imaged with this will get the name
	log "Rename the deployment volume: $ASR_FILESYSTEM_NAME" information
	/usr/sbin/diskutil rename "$TARGET_IMAGE_MOUNT" "$ASR_FILESYSTEM_NAME" | (while read INPUT; do log "$INPUT " detail; done)

	# Create a new, compessed, image from the intermediary one and scan for ASR.
	log "Create a read-only image" information
	
	# Put a copy of the package log into the image at /private/var/log/InstaDMG_package.log
	/bin/cp "$PKG_LOG" "$TARGET_IMAGE_MOUNT/private/var/log/InstaDMG_package.log"
	
	# unmount the image, then use convert to push it out to the desired place
	unmount_dmg "$TARGET_IMAGE_MOUNT" "Target image"
	TARGET_IMAGE_MOUNT=''
	
	if [ $DISABLE_BASE_IMAGE_CACHING == false ]; then
		# use the shadow file
		/usr/bin/hdiutil convert -ov -puppetstrings -format UDZO -imagekey zlib-level=6 -shadow "$SHADOW_FILE_LOCATION" -o "${ASR_FOLDER}/$ASR_OUPUT_FILE_NAME" "$TARGET_IMAGE_FILE" | (while read INPUT; do log "$INPUT " detail; done)
	else
		# there is no shadow file to use, so the scratch file should be the one
		/usr/bin/hdiutil convert -ov -puppetstrings -format UDZO -imagekey zlib-level=6 -o "${ASR_FOLDER}/$ASR_OUPUT_FILE_NAME" "$SHADOW_FILE_LOCATION" | (while read INPUT; do log "$INPUT " detail; done) 
	fi
	
	log "Scanning image for ASR: ${ASR_FOLDER}/$ASR_OUPUT_FILE_NAME" information
	/usr/sbin/asr imagescan --verbose --source "${ASR_FOLDER}/$ASR_OUPUT_FILE_NAME" 2>&1  | (while read INPUT; do log "$INPUT " detail; done)
	log "ASR image scan complete" information

}

# restore DMG to test partition
restore_image() {
	log "Restoring ASR image to test partition" section
	/usr/sbin/asr restore --verbose --source "${ASR_FOLDER}/$ASR_OUPUT_FILE_NAME" --target "$TESTING_TARGET_VOLUME" --erase --nocheck --noprompt | (while read INPUT; do log "$INPUT " detail; done)
	if [ $? -ne 0 ]; then
		log "Failed to restore image to: $TESTING_TARGET_VOLUME" error
		exit 1
	fi
}

# set test partition to be the boot partition
set_boot_test() {
	log "Blessing test partition: $TESTING_TARGET_VOLUME" section
	/usr/sbin/bless --mount "$TESTING_TARGET_VOLUME" --setBoot | (while read INPUT; do log "$INPUT " detail; done)
}

# clean up
clean_up() {
	log "Cleaning up" section
	
	log "Ejecting images" information
	if [ ! -z "TARGET_IMAGE_MOUNT" ] && [ -d "$TARGET_IMAGE_MOUNT" ]; then
		unmount_dmg "$TARGET_IMAGE_MOUNT" "Target Disk"
		/bin/rmdir "$TARGET_IMAGE_MOUNT" 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
	fi
	
	# Unmount everything that is still mounted
	for (( workingMountCount = 0 ; workingMountCount < ${#MOUNTED_DMG_MOUNT_POINTS[@]} ; workingMountCount++ )); do
		if [ ! -z ${MOUNTED_DMG_MOUNT_POINTS[$workingMountCount]} ]; then
			unmount_dmg "${MOUNTED_DMG_MOUNT_POINTS[$workingMountCount]}" "Supporting Disk"
		fi
	done
	
	
	# TODO: close this image earlier
	if [ ! -z "$CURRENT_OS_INSTALL_MOUNT" ] && [ -d "$TARGET_IMAGE_MOUNT" ] && [ $CURRENT_OS_INSTALL_AUTOMOUNTED == true ]; then
		unmount_dmg "$CURRENT_OS_INSTALL_MOUNT" "Primary OS install disk"
		/bin/rmdir "$CURRENT_OS_INSTALL_MOUNT" 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
	fi
	
	if [ ! -z "$PACKAGE_DMG_MOUNT" ] && [ -d "$PACKAGE_DMG_MOUNT" ]; then
		unmount_dmg "$PACKAGE_DMG_MOUNT" "Target Disk"
		/bin/rmdir "$PACKAGE_DMG_MOUNT" 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
	fi
	
	if [ ! -z "$SHADOW_FILE_LOCATION" ] && [ -e "$SHADOW_FILE_LOCATION" ]; then
		log "Deleting scratch DMG" information
		/bin/rm "$SHADOW_FILE_LOCATION" | (while read INPUT; do log "$INPUT " detail; done)
	fi
	
	# TODO: close out anything else in the mount directory
	if [ ! -z "$TARGET_IMAGE_MOUNT" ] && [ -d "$TARGET_IMAGE_MOUNT" ]; then
		/bin/rmdir "$TARGET_IMAGE_MOUNT" 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
	fi
	
	if [ ! -z "$TARGET_TEMP_FOLDER" ] && [ -d "$TARGET_TEMP_FOLDER" ]; then
		/bin/rmdir "$TARGET_TEMP_FOLDER" 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
	fi
	
}

# reboot the Mac
reboot() {
	log "Restarting" section
	/sbin/shutdown -r +1
}

#<!------------------------- Main -------------------------->

while getopts "b:c:d:fhi:l:m:n:o:qrt:u:vw:yzI:J:K:" opt; do
	case $opt in
		b ) INSTALLER_FOLDER="$OPTARG";;
		c ) CUSTOM_FOLDER="$OPTARG";;
		d ) CONSOLE_LOG_LEVEL="$OPTARG";;
		f ) ENABLE_NON_PARANOID_MODE=true;;
		h ) usage 0;;
		i ) ISO_CODE="$OPTARG";;
		l ) LOG_FOLDER="$OPTARG";;
		m ) ASR_OUPUT_FILE_NAME="$OPTARG";;
		n ) ASR_FILESYSTEM_NAME="$OPTARG";;
		o ) ASR_FOLDER="$OPTARG";;
		q ) CONSOLE_LOG_LEVEL=0;;
		r ) DISABLE_CHROOT=true;;
		t ) TEMPORARY_FOLDER="$OPTARG";;
		u ) UPDATE_FOLDER="$OPTARG";;
		v ) version;;
		w ) TESTING_TARGET_VOLUME="$OPTARG";;
		y ) ENABLE_TESTING_VOLUME=true;;
		z ) DISABLE_BASE_IMAGE_CACHING=true;;
		
		I )	INSTALLER_DISK="$OPTARG";; # Set the installer disk
		J )	SUPPORTING_DISKS[${#SUPPORTING_DISKS[@]}]="$OPTARG";; # Add/set supporting disk(s)
		K ) UPDATE_FOLDERS[${#UPDATE_FOLDERS[@]}]="$OPTARG";; # Add/set update folder(s)
		
		\? ) usage;;
	esac
done

# Set the UPDATE_FOLDERS variable if not already initialized
if [ ${#UPDATE_FOLDERS[@]} -eq 0 ]; then
	UPDATE_FOLDERS[0]="$UPDATE_FOLDER"
	UPDATE_FOLDERS[1]="$CUSTOM_FOLDER"
fi


# Setup log names. The PKG log is a more consise history of what was installed.
DATE_STRING=`/bin/date +%y.%m.%d-%H.%M`
LOG_FILE="${LOG_FOLDER}/${DATE_STRING}.debug.log"		# The debug log
PKG_LOG="${LOG_FOLDER}/${DATE_STRING}.package.log"		# List of packages installed

rootcheck

log "InstaDMG build initiated" section
log "InstaDMG version $VERSION" information
log "Host OS: `/usr/bin/sw_vers -productName` `/usr/bin/sw_vers -productVersion`" information
log "Host Hardware: `/usr/sbin/system_profiler SPHardwareDataType | /usr/bin/awk '/Model Identifier/ { print $3 }'`" information
log "Output file name: $ASR_OUPUT_FILE_NAME" information
log "Output disk name: $ASR_FILESYSTEM_NAME" information

check_setup
startup

trap 'clean_up' INT TERM EXIT

find_base_os

if [ $DISABLE_BASE_IMAGE_CACHING == false ]; then
	# Try a cached image
	mount_cached_image
fi

if [ -z "$TARGET_IMAGE_MOUNT" ]; then
	mount_os_install
	create_and_mount_image
	install_system
	
	if [ $DISABLE_BASE_IMAGE_CACHING == false ]; then
		save_cached_image
		mount_cached_image
	fi
fi

log "Target OS: $TARGET_OS_NAME $TARGET_OS_REV ($TARGET_OS_REV_BUILD)" information

prepare_image

# disable image caching on 10.6
if [ $OS_REV_MAJOR -eq 6 ]; then
	log "Chroot jails do not currently work with 10.6, so disabling them" warning
	DISABLE_CHROOT=true
fi

# Install the updates from within the numbered folders inside the update folders
for (( i = 0 ; i < ${#UPDATE_FOLDERS[@]} ; i++ )); do
	install_packages_from_folder "${UPDATE_FOLDERS[$i]}"
done

clean_up_image
close_up_and_compress

# cleanup will be called through the the trap

# Automated restore options. Be careful as these can destroy data.
if [ $ENABLE_TESTING_VOLUME == true ] && [ ! -z "$TESTING_TARGET_VOLUME" ] && [ -d "$TESTING_TARGET_VOLUME" ]; then
	log "InstaDMG build initiated" section
	restore_image
	set_boot_test
	reboot
fi

log "InstaDMG Complete" section

exit 0

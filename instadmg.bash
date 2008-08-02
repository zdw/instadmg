#!/bin/bash

#
# instadmg - script to automate creating ASR disk images
#

#
# Maintained by the InstaDMG dev team @ http://code.google.com/p/instadmg/
# Latest news, releases, and user forums @ http://www.afp548.com
#

# Version 1.4b3
VERSION="1.4b3"
PROGRAM=$( (basename $0) )

#
# some defaults to get us started
#

# Set up some safety measures

IFS=' 	
'

unset -f unalias

\unalias -a

unset -f command

# set path to a known path

SYSPATH="$(command -p getconf PATH 2>/dev/null)"
if [[ -z "SYSPATH" ]]; then
	SYSPATH="/usr/bin:/bin:/usr/sbin:/sbin"
fi
PATH="$SYSPATH"; export PATH

# Set the creation date in a variable so it's consistant during execution.
CREATE_DATE=`date +%y-%m-%d`

# Default ISO code for default install language. Script default is English.
ISO_CODE="en"

# Are we installing Mac OS X . This defaults to 0 for no.
SERVER_INSTALL="0"

# Put images of your install DVDs in here
INSTALLER_FOLDER=./InstallerFiles/BaseOS

# Put naked pkg updates for the base install in here. Nested folders provide the ordering.
UPDATE_FOLDER=./InstallerFiles/BaseUpdates

# Put naked custom pkg installers here. Nested folders provide the ordering.
CUSTOM_FOLDER=./InstallerFiles/CustomPKG

# This is the final ASR destination for the image.
ASR_FOLDER=./OutputFiles

# This is where cached copies of an installed version of the base image are stored
#	They are stored using a naming convention involving the checksum of the image
BASE_IMAGE_CACHE="./Caches/BaseImageCache"
BASE_IMAGE_CACHING_ALLOWED=true # setting this to false turns off caching
# TODO: make sure that the cached images are not indexed

# This string is the intermediary image name.
DMG_BASE_NAME=`uuidgen`

# This string is the root filesystem name for the ASR image.
ASR_FILESYSTEM_NAME="InstaDMG"

# The file name of the dmg that gets created
ASR_OUPUT_FILE_NAME="${CREATE_DATE}.dmg"

# Default log location.
LOG_FOLDER=./Logs

# Default log names. The PKG log is a more consise history of what was installed.
LOG_FILE=$LOG_FOLDER/`date +%y-%m-%d--%H:%M`.log
PKG_LOG=$LOG_FOLDER/`date +%y-%m-%d--%H:%M`.pkg.log

# Default scratch image size. It should not need adjustment.
DMG_SIZE=300g

# ASR target volume. Make sure you set it to the correct thing! In a future release this, and most variables, will be a getopts parameter.
ASR_TARGET_VOLUME=/Volumes/foo

# Collect path to instadmg working directory
WORKING_DIR=`pwd`

# Handler calls are at the end of the script. Other than that you should not need to modify anything below this line.


#
# Some shell variables we need
#

export COMMAND_LINE_INSTALL=1
export CM_BUILD=CM_BUILD

#
# Variables that will be filled in durring the process
#

CURRENT_OS_INSTALL_MOUNT="" # the location where the primary installer disk is mounted

CURRENT_IMAGE_MOUNT=`/usr/bin/mktemp -d /tmp/instaDMGMount.XXXXXX` # the location where the target is mounted, we will choose this initially
SCRATCH_FILE_LOCATION="/tmp/`/usr/bin/uuidgen`.dmg" # the location of the shadow file that will be scanned for the ASR output

BASE_IMAGE_CHECKSUM="" # the checksum reported by diskutil for the OS Instal disk image
BASE_IMAGE_CACHE_FOUND=false

# Get the MacOS X version information.
OS_REV_MAJOR=`/usr/bin/sw_vers -productVersion | awk -F "." '{ print $2 }'`
OS_REV_MINOR=`/usr/bin/sw_vers -productVersion | awk -F "." '{ print $3 }'`

CPU_TYPE=`/usr/bin/arch` # CPU type of the Mac running InstaDMG

#
# Now for the meat
#

bail() {	
	#If we get here theres a problem, print the usage message and then exit with a non-zero status
	
	usage $1
}

version() {
	# Show the version number
	echo "$PROGRAM version $VERSION"
	exit 0
}

usage() {
	# Usage format
cat <<EOF
Usage:  $PROGRAM [options]

Options:
	-a <folder path>	Put the final output in this folder
	-b <folder path>	Look for the base image in this folder
	-c <folder path>	Look for custom pkgs in this folder
	-h			Print the useage information (this) and exit
	-i <iso code>		Use <iso code> for the installer language (default en)
	-l <folder path>	Set the foler to use as the log folder
	-m <name>		The file name to use for the ouput file. '.dmg' will be appended as needed.
	-n <name>		The volume name to use for the output file. Defaults to: $ASR_FILESYSTEM_NAME
	-o <folder path>	Set the foler to use as the output folder
	-q			Quiet: print only errors to the console
	-s			Enable MacOS X Server installs (not implimented)
	-u <folder path>	Use this folder as the BaseUpdates folder
	-v			Print the version number and exit
	-z			Disable caching of the base image
EOF
	if [ -z $1 ]; then
		exit 1;
	else
		exit $1
	fi
}

# Log a message - takes up to two arguments

#	The first argument is the message to send. If blank log prints the date to the standard places for the selcted log level

#	The second argument tells the type of message. The default is information. The options are:
#		section		- header announcing that a new section is being started
#		warning		- non-fatal warning
#		error		- non-recoverable error
#		information	- general information
#		detail		- verbose detail

# everything will always be logged to the full log
# depending on the second argument and the loggin levels for CONSOLE_LOG_LEVEL and PACKAGE_LOG_LEVEL the following will be logged

# Error:		always logged to everything
# Section:		CONSOLE level 1 and higher, PACKAGE level 1 and higher
# Warning:		CONSOLE level 2 and higher, PACKAGE level 1 and higher
# Information:	CONSOLE level 2 and higher, PACKAGE level 2 and higher
# Detail:		CONSOLE level 3 and higher, PACKAGE level 3 and higher
# Detail 2:		CONSOLE level 4 and higher, PACKAGE leval 4 and higher 

# Detail 2 is lines that begin with "installer:"

# commands should all have the following appended to them:
#	| (while read INPUT; do log "$INPUT " information; done)

ERROR_LOG_FORMAT="ERROR: %s\n"
SECTION_LOG_FORMAT="######%s######\n"
WARNING_LOG_FORMAT="WARNING: %s\n"
SUBPACKAGE_LOG_FORMAT="		%s\n"
INFORMATION_LOG_FORMAT="	%s\n"
DETAIL_LOG_FORMAT="		%s\n"

CONSOLE_LOG_LEVEL=2
PACKAGE_LOG_LEVEL=2

log () {
	if [ -z "$1" ] || [ "$1" == "" ] || [ "$1" == "#" ]; then
		# there is nothing to log
		return
	else
		MESSAGE="$1"
	fi
	
	if [ -z "$2" ]; then
		LEVEL="information"
	else
		LEVEL="$2"
	fi	

	if [ "$LEVEL" == "error" ]; then
		/usr/bin/printf "$SECTION_LOG_FORMAT" "$MESSAGE" | /usr/bin/tee "$LOG_FILE" "$PKG_LOG" 1>&2
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

# check to make sure we are root, installers will complain otherwise
rootcheck() {
	# Root is required to run instadmg
	if [ $EUID != 0 ]; then
		log "You must run this utility using sudo or as root!" error
		exit 64
	fi
}

check_setup () {
	# Check the language
	LANGUAGE_CODE_IS_VALID_TEMPFILE=`/usr/bin/mktemp /tmp/instaDMGTemp.XXXXXX`
	/usr/sbin/installer -listiso | /usr/bin/tr "\t" "\n" | while read LANGUAGE_CODE
	do
		if [ "$ISO_CODE" == "$LANGUAGE_CODE" ]; then
			/bin/echo "true" > "$LANGUAGE_CODE_IS_VALID_TEMPFILE"
		fi
	done
	if [ ! -s "$LANGUAGE_CODE_IS_VALID_TEMPFILE" ]; then
		log "The ISO language code $ISO_CODE is not recognized by the Apple installer" error
		exit 1
	fi
	
	# if the ASR_OUPUT_FILE_NAME does not end in .dmg, add it
	if [ `/bin/echo "$ASR_OUPUT_FILE_NAME" | /usr/bin/awk 'tolower($1) ~ /.*\.dmg$/ { print "true" }'` != "true" ]; then
		ASR_OUPUT_FILE_NAME="$ASR_OUPUT_FILE_NAME.dmg"
	fi
}

# Mount the OS source image.
# If you have some wacky disk name then change this as needed.

mount_os_install() {
	log "Mounting Mac OS X installer image" section
	
	# to get around bash variable scope difficulties we will be stashing things in tempfiles
	OS_INSTALL_LOCATION_TEMPFILE=`/usr/bin/mktemp /tmp/instaDMGTemp.XXXXXX`
	BASE_IMAGE_CACHING_ALLOWED_TEMPFILE=`/usr/bin/mktemp /tmp/instaDMGTemp.XXXXXX`
	BASE_IMAGE_CHECKSUM_TEMPFILE=`/usr/bin/mktemp /tmp/instaDMGTemp.XXXXXX`
	BASE_IMAGE_CACHE_FOUND_TEMPFILE=`/usr/bin/mktemp /tmp/instaDMGTemp.XXXXXX`
	BASE_IMAGE_FILE_TEMPFILE=`/usr/bin/mktemp /tmp/instaDMGTemp.XXXXXX`
	
	/usr/bin/find "$INSTALLER_FOLDER" -iname "*.dmg" | while read IMAGE_FILE
	do
		# Look to see if this is the first installer disk
		# TODO: look at the dmg (internally) to see if it looks like the installer rather than relying on the name
		# TODO: somehow make sure that the base installer disk is first
		
		if [ "$IMAGE_FILE" == "$INSTALLER_FOLDER/Mac OS X Install Disc 1.dmg" ] || [ "$IMAGE_FILE" == "$INSTALLER_FOLDER/Mac OS X Install DVD.dmg" ]; then
			# we have a primary disk image
			
			# check it to see if we already have a built form of this one cached
			if [ $BASE_IMAGE_CACHING_ALLOWED == true ]; then
				# first make sure that the folder exists
				
				if [ -x "$BASE_IMAGE_CACHE" ]; then
					if [ -d "$BASE_IMAGE_CACHE" ]; then
						FOUND_CACHE=true
					else
						# there was something other than a folder at the location, so we need to bail out of the cache code
						log "Caching was enabled, but the item at the cache location was not a folder: $BASE_IMAGE_CACHE" warning
						FOUND_CACHE=false
						BASE_IMAGE_CACHING_ALLOWED=false
					fi
				else
					# we didn't find the cache folder, so will attempt to create it
					if [ "`/bin/mkdir -p "$BASE_IMAGE_CACHE" 2>&1`" != "" ]; then # if there was any output, it was from an error
						log "Unable to create cache folder at: $BASE_IMAGE_CACHE" warning
						FOUND_CACHE=false
						BASE_IMAGE_CACHING_ALLOWED=false
					fi						
				fi
				
				if [ $FOUND_CACHE == true ]; then
					BASE_IMAGE_CHECKSUM=`/usr/bin/hdiutil imageinfo "$IMAGE_FILE" | /usr/bin/awk '/^Checksum Value:/ { print $3 }' | /usr/bin/sed 's/\\$//'`
					# TODO: check this line on 10.4 and beyond 10.5
					
					# in order to make sure we get the right cached image, we have to know what installerChoices.xml file we are using
					# TODO: get rid of this duplication of effort in finding the installerChoices.xml file
					INSTALLER_CHOICES_FILE=""
					if [ $OS_REV_MAJOR -gt 4 ] && [ -e "$INSTALLER_FOLDER/InstallerChoices.xml" ]; then
						INSTALLER_CHOICES_FILE="$INSTALLER_FOLDER/InstallerChoices.xml"
					fi
					
					# if there is an INSTALLER_CHOICES_FILE, append ":" and the sha1 checksum to the file
					if [ ! -z "$INSTALLER_CHOICES_FILE" ]; then
						INSTALLER_CHOICES_CHEKSUM=`/usr/bin/openssl dgst -sha1 "$INSTALLER_CHOICES_FILE" | awk 'sub(".*= ", "")'`
						BASE_IMAGE_CHECKSUM="$BASE_IMAGE_CHECKSUM:$INSTALLER_CHOICES_CHEKSUM"
					fi
					
					if [ ! -z "$BASE_IMAGE_CHECKSUM" ]; then # just in case the image is invalid or somehow does not have a checksum
						/bin/echo "$BASE_IMAGE_CHECKSUM" > "$BASE_IMAGE_CHECKSUM_TEMPFILE"
						
						if [ -e "$BASE_IMAGE_CACHE/$BASE_IMAGE_CHECKSUM.dmg" ]; then
							# here we have found the appropriate image, we will mount it with a "shadow" file, and make changes into that.
							# TODO: better error checking if the image is not mountable
							# TODO: check to see if the disk is already mounted
							
							/bin/echo "$BASE_IMAGE_CACHE/$BASE_IMAGE_CHECKSUM.dmg" > "$BASE_IMAGE_FILE_TEMPFILE"
							
							# in this case our scratch file will be a shadow mounted dmg
							
							# both the SCRATCH_FILE_LOCATION and the CURRENT_IMAGE_MOUNT are pre-determined
							log "Mounting the shadow file ($SCRATCH_FILE_LOCATION) onto the image." information
							/usr/bin/hdiutil mount "$BASE_IMAGE_CACHE/$BASE_IMAGE_CHECKSUM.dmg" -nobrowse -puppetstrings -mountpoint "$CURRENT_IMAGE_MOUNT" -shadow "$SCRATCH_FILE_LOCATION" | (while read INPUT; do log "$INPUT " detail; done)
							
							# signal that this is a cached image
							`/bin/echo "true" > "$BASE_IMAGE_CACHE_FOUND_TEMPFILE"`
							
							# we don't need to cycle over any other files, but we do need to close up things, and save our variables
							break
						fi
					
					else
						# there was no such beast in the cache directory
						FOUND_CACHE=false
						BASE_IMAGE_CACHING_ALLOWED=false
					fi
				fi
			fi
			
			# mount the image
			
			# but first we have to make sure that it is not already mounted
			/usr/bin/hdiutil info | while read HDIUTIL_LINE
			do
				if [ `/bin/echo "$HDIUTIL_LINE" | /usr/bin/grep -c '================================================'` -eq 1 ]; then
					# this is the marker for a new section, so we need to clear things out
					IMAGE_LOCATION=""
					MOUNTED_IMAGES=""
			
				elif [ "`/bin/echo "$HDIUTIL_LINE" | /usr/bin/awk '/^image-path/'`" != "" ]; then
					IMAGE_LOCATION=`/bin/echo "$HDIUTIL_LINE" | /usr/bin/awk 'sub("^image-path[[:space:]]+:[[:space:]]+", "")'`
					
					# check the inodes to see if we are pointing at the same file
					if [ "`/bin/ls -Li "$IMAGE_LOCATION" | awk '{ print $1 }'`" != "`/bin/ls -Li "$IMAGE_FILE" | awk '{ print $1 }'`" ]; then
						# this is not the droid we are looking for
						IMAGE_LOCATION=""
						
						# if it is the same thing, then we let it through to get the mount point below
					fi
				elif [ "$IMAGE_LOCATION" != "" ] && [ "`/bin/echo "$HDIUTIL_LINE" | /usr/bin/awk '/\/dev\/.+[[:space:]]+Apple_HFS[[:space:]]+\//'`" != "" ]; then
					# find the mount point
					CURRENT_OS_INSTALL_MOUNT=`/bin/echo "$HDIUTIL_LINE" | /usr/bin/awk 'sub("/dev/.+[[:space:]]+Apple_HFS[[:space:]]+", "")'`
					`/bin/echo "$CURRENT_OS_INSTALL_MOUNT" > "$OS_INSTALL_LOCATION_TEMPFILE"` # to get around bash variable scope difficulties
					# Here we are done!
					log "The main OS Installer Disk was already mounted at: $CURRENT_OS_INSTALL_MOUNT" warning
				fi
			done
			
			if [ "$CURRENT_OS_INSTALL_MOUNT" == "" ]; then
				# since it was not already mounted, we have to mount it
				#	we are going to mount it non-browsable, so it does not appear in the finder, and we are going to mount it to a temp folder
				
				CURRENT_OS_INSTALL_MOUNT=`/usr/bin/mktemp -d /tmp/instaDMGMount.XXXXXX`
				log "Mounting the main OS Installer Disk from: $IMAGE_FILE at: $CURRENT_OS_INSTALL_MOUNT" information
				/usr/bin/hdiutil mount "$IMAGE_FILE" -readonly -nobrowse -mountpoint "$CURRENT_OS_INSTALL_MOUNT" | (while read INPUT; do log $INPUT detail; done)
				`/bin/echo "$CURRENT_OS_INSTALL_MOUNT" > "$OS_INSTALL_LOCATION_TEMPFILE"`
				# TODO: check to see if there was a problem
			fi
	
		else
			# this is probably a supporting disk, so we have to mount it browseable
			# TODO: add this mount to the list of things we are going to unmount
			# TODO: use union mounting to see if we can't co-mount this
			log "Mounting a support disk from $INSTALLER_FOLDER/$IMAGE_FILE" information
			/usr/bin/hdiutil mount "$IMAGE_FILE" -readonly | (while read INPUT; do log $INPUT detail; done)
		fi
	done
	
	# handle the flags that we got left to handle bash variable scope difficulties
	if [ -s "$BASE_IMAGE_CACHING_ALLOWED_TEMPFILE" ]; then
		BASE_IMAGE_CACHING_ALLOWED=false
	fi
	if [ -s "$BASE_IMAGE_FILE_TEMPFILE" ]; then
		BASE_IMAGE_FILE=`/bin/cat "$BASE_IMAGE_FILE_TEMPFILE"`
	fi
	if [ -s "$BASE_IMAGE_CACHE_FOUND_TEMPFILE" ]; then
		BASE_IMAGE_CACHE_FOUND=true
	fi
	if [ -s "$BASE_IMAGE_CHECKSUM_TEMPFILE" ]; then
		BASE_IMAGE_CHECKSUM=`/bin/cat "$BASE_IMAGE_CHECKSUM_TEMPFILE"`
	fi
	if [ -s "$OS_INSTALL_LOCATION_TEMPFILE" ]; then
		CURRENT_OS_INSTALL_MOUNT=`/bin/cat "$OS_INSTALL_LOCATION_TEMPFILE"`
	fi
	
	# and clean up the tempfiles
	/bin/rm "$OS_INSTALL_LOCATION_TEMPFILE"
	/bin/rm "$BASE_IMAGE_CACHING_ALLOWED_TEMPFILE"
	/bin/rm "$BASE_IMAGE_CHECKSUM_TEMPFILE"
	/bin/rm "$BASE_IMAGE_CACHE_FOUND_TEMPFILE"
	/bin/rm "$BASE_IMAGE_FILE_TEMPFILE"
	
	if [ ! -d "$CURRENT_OS_INSTALL_MOUNT/System/Installation/Packages" ] && [ $BASE_IMAGE_CACHE_FOUND == false ]; then
		log "ERROR: the main install disk was not sucessfully mounted!" 
		exit 1
	fi
	
	log "Mac OS X installer image mounted" information
}

# setup and create the DMG.

create_and_mount_image() {
	# first we need to check if we are running off a cached build
	if [ ! -z "$CURRENT_IMAGE_MOUNT" ] && [ -d "$CURRENT_IMAGE_MOUNT/System" ]; then
		log "Running from cached image ($BASE_IMAGE_FILE)" information
		return
	fi
	
	log "Creating intermediary disk image" section
	
	SCRATCH_FILE_LOCATION=`/usr/bin/mktemp /tmp/instaDMGTemp.XXXXXX`
	/bin/mv "$SCRATCH_FILE_LOCATION" "$SCRATCH_FILE_LOCATION.sparseimage" # since 
	SCRATCH_FILE_LOCATION="$SCRATCH_FILE_LOCATION.sparseimage"
	
	/usr/bin/hdiutil create -ov -size $DMG_SIZE -type SPARSE -fs HFS+ "$SCRATCH_FILE_LOCATION" | (while read INPUT; do log "$INPUT " detail; done)
	CURRENT_IMAGE_MOUNT_DEV=`/usr/bin/hdiutil attach "$SCRATCH_FILE_LOCATION" | /usr/bin/head -n 1 |  /usr/bin/awk '{ print $1 }'`
	log "Image mounted at $CURRENT_IMAGE_MOUNT_DEV" 
	
	# Format the DMG so that the Installer will like it 

	# Determine the platform

	if [ "$CPU_TYPE" == "ppc" ]; then 
#=======
	# Double evaluations was killing the script.
	#if [ "$CPU_TYPE" = "ppc" ]; then 

		log 'Running on PPC Platform: Setting format to APM' information
		/usr/sbin/diskutil eraseDisk "Journaled HFS+" $DMG_BASE_NAME APMformat $CURRENT_IMAGE_MOUNT_DEV | (while read INPUT; do log "$INPUT " detail; done)

	elif  [ "$CPU_TYPE" == "i386" ]; then
#=======
	#elif  [ "$CPU_TYPE" = "i386" ]; then

		log 'Running on Intel Platform: Setting format to GPT' information
		/usr/sbin/diskutil eraseDisk "Journaled HFS+" $DMG_BASE_NAME GPTFormat $CURRENT_IMAGE_MOUNT_DEV | (while read INPUT; do log "$INPUT " detail; done)
	else
		log "Unknown CPU type: $CPU_TYPE. Unable to continue" error
		exit 1
	fi
	# since this unmounts the disk, and then auto-mounts it at the end, we have to re-mount it to get it hidden again
	/usr/bin/hdiutil eject "$CURRENT_IMAGE_MOUNT_DEV" | (while read INPUT; do log $INPUT detail; done)

	/usr/bin/hdiutil mount "$SCRATCH_FILE_LOCATION" -noverify -nobrowse -mountpoint "$CURRENT_IMAGE_MOUNT" | (while read INPUT; do log "$INPUT " detail; done)
	
	log "Intimediary image creation complete" information
}

# Install from installation media to the DMG
# The you can adjust the default language with the ISO_CODE variable.
#
# If you are running on 10.5 then InstaDMG will check for an InstallerChoices.xml file.
# This file will let you take control over what gets installed from the OSInstall.mpkg.
# Just place the file in the same directory as your installer image.

install_system() {
	log "Beginning Installation from $CURRENT_OS_INSTALL_MOUNT" section
	
	if [ $BASE_IMAGE_CACHING_ALLOWED == true ] && [ $BASE_IMAGE_CACHE_FOUND == true ]; then
		log "Using Cached image, so skipping OS installation" information
		return
	fi
	
	if [ $OS_REV_MAJOR -eq 4 ]; then
		log "Running on Tiger. Not checking for InstallerChoices.xml file" information
		/usr/sbin/installer -verbose -pkg "$CURRENT_OS_INSTALL_MOUNT/System/Installation/Packages/OSInstall.mpkg" -target $CURRENT_IMAGE_MOUNT -lang $ISO_CODE | (while read INPUT; do log "$INPUT " detail; done)
	elif [ $OS_REV_MAJOR -gt 4 ]; then
		log "I'm running on Leopard or later. Checking for InstallerChoices.xml file" 
		if [ -e "$INSTALLER_FOLDER/InstallerChoices.xml" ]; then
			log "InstallerChoices.xml file found. Applying Choices" information
			/usr/sbin/installer -verbose -applyChoiceChangesXML "$INSTALLER_FOLDER/InstallerChoices.xml" -pkg "$CURRENT_OS_INSTALL_MOUNT/System/Installation/Packages/OSInstall.mpkg" -target "$CURRENT_IMAGE_MOUNT" -lang "$ISO_CODE" | (while read INPUT; do log "$INPUT " detail; done)
		else
			log "No InstallerChoices.xml file found. Installing full mpkg" information
			/usr/sbin/installer -verbose -pkg "$CURRENT_OS_INSTALL_MOUNT/System/Installation/Packages/OSInstall.mpkg" -target "$CURRENT_IMAGE_MOUNT" -lang "$ISO_CODE" | (while read INPUT; do log "$INPUT " detail; done)
		fi
	else
		log "Unknown operating system. Unable to procede" error
		exit 1
	fi
	log "Base OS installed" information
		
	if [ $BASE_IMAGE_CACHING_ALLOWED == true ]; then 
		# if we are at this point we need to close the image, move it to the cached folder, and then re-open with a shadow-file
		log "Compacting and saving cached image to: $BASE_IMAGE_CACHE/$BASE_IMAGE_CHECKSUM.dmg" information
		
		BASE_IMAGE_FILE="$BASE_IMAGE_CACHE/$BASE_IMAGE_CHECKSUM.dmg"
		
		# unmount the image
		/usr/bin/hdiutil eject -force "$CURRENT_IMAGE_MOUNT" | (while read INPUT; do log "$INPUT " detail; done)
		
		# move the image to the cached folder with the appropriate name
		/bin/mv "$SCRATCH_FILE_LOCATION" "$BASE_IMAGE_FILE"
		
		# NOTE: backing off this code for the moment... does not seem happy
		# compress the image and store it in the new location
		#/usr/bin/hdiutil convert -format UDZO -imagekey zlib-level=6 -o "$BASE_IMAGE_FILE" "$SCRATCH_FILE_LOCATION" | (while read INPUT; do log "$INPUT " detail; done)
		
		# set the appropriate metadata on the file so that time-machine does not back it up
		/usr/bin/xattr -w com.apple.metadata:com_apple_backup_excludeItem com.apple.backupd
		
		# remount the image with the shadow file (will be created automatically)
		log "Remounting the image with a shadow file ($SCRATCH_FILE_LOCATION)" information
		/usr/bin/hdiutil mount "$BASE_IMAGE_FILE" -nobrowse -mountpoint "$CURRENT_IMAGE_MOUNT" -shadow "$SCRATCH_FILE_LOCATION" | (while read INPUT; do log "$INPUT " detail; done)
		# TODO: error handling
	fi
}

# install packages from a folder of folders (01, 02, 03...etc)
install_packages_from_folder() {
	SELECTED_FOLDER="$1"
	
	log "Beginning Update Installs from $SELECTED_FOLDER" section

	if [ "$SELECTED_FOLDER" == "" ]; then
		log "install_packages_from_folder called without folder" error
		exit 1;
	fi
	
	/bin/ls -A1 "$SELECTED_FOLDER" | /usr/bin/awk "/^[[:digit:]]+$/" | while read ORDERED_FOLDER
	do
		/usr/bin/find -L "$SELECTED_FOLDER/$ORDERED_FOLDER" -depth 1 -iname "*pkg" | /usr/bin/awk -F "\n" 'tolower($1) ~ /\.(m)?pkg/ && !/\/\._/' | while read UPDATE_PKG
		do
			if [ -e "$SELECTED_FOLDER/$ORDERED_FOLDER/InstallerChoices.xml" ]; then
				CHOICES_FILE="InstallerChoices.xml"
				# TODO: better handle multiple pkg's and InstallerChoice files named for the file they should handle
			fi
			
			if [ $OS_REV_MAJOR -le 4 ]; then
				CHOICES_FILE="" # 10.4 can not use them
			fi			
			
			if [ "$CHOICES_FILE" != "" ]; then
				log "Installing $UPDATE_PKG with XML Choices file: $CHOICES_FILE" information
				/usr/sbin/installer -verbose -applyChoiceChangesXML "$SELECTED_FOLDER/$ORDERED_FOLDER/$CHOICES_FILE" -pkg "$UPDATE_PKG" -target "$CURRENT_IMAGE_MOUNT" | (while read INPUT; do log "$INPUT " detail; done)
			else
				log "Installing $UPDATE_PKG" information
				/usr/sbin/installer -verbose -pkg "$UPDATE_PKG" -target "$CURRENT_IMAGE_MOUNT" | (while read INPUT; do log "$INPUT " detail; done)
			fi
		done
	done
}

# clean up some generic installer mistakes
clean_up_image() {
	log "Correcting some generic installer errors" section
	
	# find all the symlinks that are pointing to $CURRENT_IMAGE_MOUNT, and make them point at the "root"
	log "Correcting symlinks that point off the disk" information
	/usr/bin/find -x "$CURRENT_IMAGE_MOUNT" -type l | while read THIS_LINK
	do
		if [ `/usr/bin/readlink "$THIS_LINK" | /usr/bin/grep -c "$CURRENT_IMAGE_MOUNT"` -gt 0 ]; then
		
			log "Correcting soft-link: $THIS_LINK" detail
			CORRECTED_LINK=`/usr/bin/readlink "$THIS_LINK" | /usr/bin/awk "sub(\"$CURRENT_IMAGE_MOUNT\", \"\") { print }"`
			
			/bin/rm "$THIS_LINK"
			/bin/ln -fs "$CORRECTED_LINK" "$THIS_LINK" | (while read INPUT; do log "$INPUT " detail; done)
		
		fi
	done
	
	# make sure that we have not left any open files behind
	log "Closing programs that have opened files on the disk" information
	/usr/sbin/lsof | /usr/bin/grep "$CURRENT_IMAGE_MOUNT/" | /usr/bin/awk '{ print $2 }' | /usr/bin/sort -u | /usr/bin/xargs /bin/kill 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
}

# close up the DMG, compress and scan for restore
close_up_and_compress() {
	log "Creating the deployment DMG and scanning for ASR" section
	
	# We'll rename the newly installed system so that computers imaged with this will get the name
	log "Rename the deployment volume: $ASR_FILESYSTEM_NAME" information
	/usr/sbin/diskutil rename "$CURRENT_IMAGE_MOUNT" "$ASR_FILESYSTEM_NAME" | (while read INPUT; do log "$INPUT " detail; done)

	# Create a new, compessed, image from the intermediary one and scan for ASR.
	log "Create a read-only image"
	
	# unmount the image, then use convert to push it out to the desired place
	/usr/bin/hdiutil eject -force "$CURRENT_IMAGE_MOUNT" | (while read INPUT; do log "$INPUT " detail; done)
	if [ $BASE_IMAGE_CACHING_ALLOWED == true ]; then
		# use the shadow file
		/usr/bin/hdiutil convert -puppetstrings -format UDZO -imagekey zlib-level=6 -shadow "$SCRATCH_FILE_LOCATION" -o "${ASR_FOLDER}/$ASR_OUPUT_FILE_NAME" "$BASE_IMAGE_FILE" | (while read INPUT; do log "$INPUT " detail; done)
	else
		# there is no shadow file to use, so the scratch file should be the one
		/usr/bin/hdiutil convert -puppetstrings -format UDZO -imagekey zlib-level=6 -o "${ASR_FOLDER}/$ASR_OUPUT_FILE_NAME" "$SCRATCH_FILE_LOCATION" | (while read INPUT; do log "$INPUT " detail; done) 
	fi
	
	log "Scanning image for ASR: ${ASR_FOLDER}/$ASR_OUPUT_FILE_NAME" information
	/usr/sbin/asr imagescan --verbose --source "${ASR_FOLDER}/$ASR_OUPUT_FILE_NAME" 2>&1  | (while read INPUT; do log "$INPUT " detail; done)
	log "ASR image scan complete" information

}

# restore DMG to test partition
restore_image() {
	log "Restoring ASR image to test partition" section
	/usr/sbin/asr --verbose --source "${ASR_FOLDER}/$ASR_OUPUT_FILE_NAME" --target "$ASR_TARGET_VOLUME" --erase --nocheck --noprompt | (while read INPUT; do log "$INPUT " detail; done)
	log "ASR image restored..." information
}

# set test partition to be the boot partition
set_boot_test() {
	log "Blessing test partition" section
	/usr/sbin/bless "--mount $CURRENT_IMAGE_MOUNT --setBoot" | (while read INPUT; do log "$INPUT " detail; done)
	log "Test partition blessed" information
}

# clean up
clean_up() {
	log "Cleaning up" section
	
	log "Ejecting images" information
	if [ -f "$CURRENT_IMAGE_MOUNT/System" ]; then
		/usr/bin/hdiutil eject "$CURRENT_IMAGE_MOUNT" | (while read INPUT; do log "$INPUT " detail; done)
	fi
	# TODO: close this image earlier
	if [ ! -z "$CURRENT_OS_INSTALL_MOUNT" ]; then
		/usr/bin/hdiutil eject "$CURRENT_OS_INSTALL_MOUNT" | (while read INPUT; do log "$INPUT " detail; done)
	fi
	
	log "Removing scratch DMG" 
	if [ ! -z "$SCRATCH_FILE_LOCATION" ] && [ -e "$SCRATCH_FILE_LOCATION" ]; then
		/bin/rm "$SCRATCH_FILE_LOCATION" | (while read INPUT; do log "$INPUT " detail; done)
	fi
	
}

# reboot the Mac
reboot() {
	log "Restarting" section
	/sbin/shutdown -r +1
}

# Call the handlers as needed to make it all happen.

while getopts "a:b:c:hi:l:m:n:o:qsu:vz" opt
do
	case $opt in
		a )	ASR_FOLDER="$OPTARG";;
		b ) INSTALLER_FOLDER="$OPTARG";;
		c ) CUSTOM_FOLDER="$OPTARG";;	
		h ) usage;;
		i ) ISO_CODE="$OPTARG";;
		l ) LOG_FOLDER="$OPTARG";;
		m ) ASR_OUPUT_FILE_NAME="$OPTARG";;
		n ) ASR_FILESYSTEM_NAME="$OPTARG";;
		o ) ASR_FOLDER="$OPTARG";;
		q ) CONSOLE_LOG_LEVEL=0;;
		s ) SERVER_INSTALL="1";;
		u ) UPDATE_FOLDER="$OPTARG";;
		v ) version;;
		z ) BASE_IMAGE_CACHING_ALLOWED=false;;
		\? ) usage;;
	esac
done
check_setup

rootcheck

log "InstaDMG build initiated" section

mount_os_install
create_and_mount_image
install_system

install_packages_from_folder "$UPDATE_FOLDER"
install_packages_from_folder "$CUSTOM_FOLDER"

clean_up_image
close_up_and_compress
clean_up

# Automated restore options. Be careful as these can destroy data.
# restore_image
# set_boot_test
# reboot

log "InstaDMG Complete" section

exit 0

#!/bin/bash

#
# instadmg - script to automate creating ASR disk images
#

#
# Josh Wisenbaker - macshome@afp548.com - Maintainer
#

# Version 1.4b2

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

# Am I running on Leopard? This will equal 1 on 10.5 and 0 on everything else.
OS_REV=`/usr/bin/sw_vers | /usr/bin/grep -c 10.5`

# CPU type of the Mac running InstaDMG. If we are on Intel this will equal 1. Otherwise it equals 0.
CPU_TYPE=`arch | /usr/bin/grep -c i386`

# Default ISO code for default install language. Script default is English.
ISO_CODE="en"

# Are we installing Mac OS X Server. This defaults to 0 for no.
SERVER_INSTALL="0"

# Put images of your install DVDs in here
INSTALLER_FOLDER=./BaseOS

# Put naked pkg updates for the base install in here. Nested folders provide the ordering.
UPDATE_FOLDER=./BaseUpdates

# Put naked custom pkg installers here. Nested folders provide the ordering.
CUSTOM_FOLDER=./CustomPKG

# This is the final ASR destination for the image.
ASR_FOLDER=./ASR_Output

# This is where DMG scratch is done. Set this to whatever you want.
DMG_SCRATCH=./DMG_Scratch

# This string is the intermediary image name.
DMG_BASE_NAME=`uuidgen`

# This string is the root filesystem name for the intermediary image. Deprecated in favor of DMG_BASE_NAME
# DMG_FS_NAME="InstaDMG_Temp"

# This string is the root filesystem name for the ASR image.
ASR_FS_NAME="InstaDMG"

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
# Now for the meat
#

# check to make sure we are root, can't do these things otherwise

check_root() {
    if [ `whoami` != "root" ]
    then
        /bin/echo "you need to be root to do this so use sudo"
        exit 0;
    fi
}

# setup and create the DMG.

create_and_mount_image() {
	/bin/echo "#############################################################" >> $LOG_FILE
	/bin/echo "InstaDMG build initiated" >> $LOG_FILE
	/bin/echo "#############################################################" >> $PKG_LOG
	/bin/echo "InstaDMG build initiated" >> $PKG_LOG
	/bin/echo "" >> $LOG_FILE
	/bin/echo $CREATE_DATE >> $LOG_FILE
	/bin/echo "" >> $LOG_FILE
	/bin/echo "" >> $PKG_LOG
	/bin/echo "####Creating intermediary disk image#####" >> $LOG_FILE
	/bin/date +%H:%M:%S >> $LOG_FILE
	/bin/echo "" >> $LOG_FILE
	[ -e ${DMG_BASE_NAME}.${CREATE_DATE}.sparseimage ] && $CREATE_DATE		
	/usr/bin/hdiutil create -size $DMG_SIZE -type SPARSE -fs HFS+ $DMG_SCRATCH/${DMG_BASE_NAME}.${CREATE_DATE} >> $LOG_FILE
	CURRENT_IMAGE_MOUNT_DEV=`/usr/bin/hdiutil attach $DMG_SCRATCH/$DMG_BASE_NAME.$CREATE_DATE.sparseimage | /usr/bin/head -n 1 |  /usr/bin/awk '{ print $1 }'`
	/bin/echo "Image mounted at $CURRENT_IMAGE_MOUNT_DEV" >> $LOG_FILE
	/bin/echo "" >> $LOG_FILE
	
	# Format the DMG so that the Installer will like it 

	# Determine the platform
		if [ $CPU_TYPE -eq 0 ]; then 
			/bin/echo "I'm Running on PPC Platform" >> $LOG_FILE
			/bin/echo "Setting format to APM" >> $LOG_FILE
			/bin/echo "" >> $LOG_FILE
			
			#(PPC Mac)
				/usr/sbin/diskutil eraseDisk "Journaled HFS+" $DMG_BASE_NAME APMformat $CURRENT_IMAGE_MOUNT_DEV >> $LOG_FILE
				/bin/echo "" >> $LOG_FILE
				CURRENT_IMAGE_MOUNT=/Volumes/$DMG_BASE_NAME
		else 
			/bin/echo "I'm Running on Intel Platform" >> $LOG_FILE
			/bin/echo "Setting format to GPT" >> $LOG_FILE
			/bin/echo "" >> $LOG_FILE
			#(Intel Mac)
				/usr/sbin/diskutil eraseDisk "Journaled HFS+" $DMG_BASE_NAME GPTFormat $CURRENT_IMAGE_MOUNT_DEV >> $LOG_FILE
				/bin/echo "" >> $LOG_FILE
				CURRENT_IMAGE_MOUNT=/Volumes/$DMG_BASE_NAME
		fi
		/bin/echo "Intimediary image creation complete" >> $LOG_FILE
		/bin/date +%H:%M:%S >> $LOG_FILE
		/bin/echo "" >> $LOG_FILE
		/bin/echo "" >> $LOG_FILE
}

# Mount the OS source image.
# If you have some wacky disk name then change this as needed.

mount_os_install() {
	/bin/echo "#####Mounting Mac OS X installer image#####" >> $LOG_FILE
	/bin/date +%H:%M:%S >> $LOG_FILE
	/bin/echo "" >> $LOG_FILE
	
	TEMPFILE=`/usr/bin/mktemp /tmp/instaDMGTemp.XXXXXX` # to get around bash variable scope difficulties
	
	/usr/bin/find "$INSTALLER_FOLDER" -iname "*.dmg" | while read IMAGE_FILE
	do
		# Look to see if this is the first installer disk
		# TODO: look at the dmg (internally) to see if it looks like the installer rather than relying on the name
		if [ "$IMAGE_FILE" == "$INSTALLER_FOLDER/Mac OS X Install Disc 1.dmg" ] || [ "$IMAGE_FILE" == "$INSTALLER_FOLDER/Mac OS X Install DVD.dmg" ]; then
			# this is the installer disk, and we can mount it hidden
			
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
					`/bin/echo "$CURRENT_OS_INSTALL_MOUNT" > "$TEMPFILE"` # to get around bash variable scope difficulties
					# Here we are done!
					/bin/echo "	The main OS Installer Disk was already mounted at: $CURRENT_OS_INSTALL_MOUNT" | /usr/bin/tee -a $LOG_FILE
				fi
			done
			
			if [ "$CURRENT_OS_INSTALL_MOUNT" == "" ]; then
				# since it was not already mounted, we have to mount it
				#	we are going to mount it non-browsable, so it does not appear in the finder, and we are going to mount it to a temp folder
				
				CURRENT_OS_INSTALL_MOUNT=`/usr/bin/mktemp -d /tmp/instaDMGMount.XXXXXX`
				/bin/echo "	Mounting the main OS Installer Disk from: $IMAGE_FILE at: $CURRENT_OS_INSTALL_MOUNT" | /usr/bin/tee -a $LOG_FILE
				/usr/bin/hdiutil mount "$IMAGE_FILE" -readonly -nobrowse -mountpoint "$CURRENT_OS_INSTALL_MOUNT" | /usr/bin/tee -a $LOG_FILE
				`/bin/echo "$CURRENT_OS_INSTALL_MOUNT" > "$TEMPFILE"` # to get arround bash variable scope difficulties
			fi
	
		else
			# this is probably a supporting disk, so we have to mount it browseable
			# TODO: add this mount to the list of things we are going to unmount
			# TODO: use union mounting to see if we can't co-mount this
			/bin/echo "	Mounting a support disk from $INSTALLER_FOLDER/$IMAGE_FILE" | /usr/bin/tee -a $LOG_FILE
			/usr/bin/hdiutil mount "$IMAGE_FILE" -readonly | /usr/bin/tee -a $LOG_FILE >&4
		fi
	done
	
	CURRENT_OS_INSTALL_MOUNT=`/bin/cat "$TEMPFILE"` # to get arround bash variable scope difficulties
	/bin/rm "$TEMPFILE"
	
	if [ ! -d "$CURRENT_OS_INSTALL_MOUNT/System/Installation/Packages" ]; then
		/bin/echo "ERROR: the main install disk was not sucessfully mounted!" | /usr/bin/tee -a $LOG_FILE
		exit 1
	fi
	
	/bin/echo "Mac OS X installer image mounted" >> $LOG_FILE
	/bin/date +%H:%M:%S >> $LOG_FILE
	/bin/echo "" >> $LOG_FILE
	/bin/echo "" >> $LOG_FILE
}

# Install from installation media to the DMG
# The you can adjust the default language with the ISO_CODE variable.
#
# If you are running on 10.5 then InstaDMG will check for an InstallerChoices.xml file.
# This file will let you take control over what gets installed from the OSInstall.mpkg.
# Just place the file in the same directory as the instadmg script.

install_system() {
	/bin/echo "#####Beginning Installation from $CURRENT_OS_INSTALL_MOUNT#####" >> $LOG_FILE
	/bin/echo "#####Beginning Installation from $CURRENT_OS_INSTALL_MOUNT#####" >> $PKG_LOG
	/bin/date +%H:%M:%S >> $LOG_FILE
	/bin/date +%H:%M:%S >> $PKG_LOG
	/bin/echo "" >> $LOG_FILE
	/bin/echo "" >> $PKG_LOG
	if [ $OS_REV -eq 0 ]; then
		/bin/echo "I'm running on Tiger. Not checking for InstallerChoices.xml file" >> $LOG_FILE
		/bin/echo "" >> $LOG_FILE
		/usr/sbin/installer -verbose -pkg "$CURRENT_OS_INSTALL_MOUNT/System/Installation/Packages/OSInstall.mpkg" -target $CURRENT_IMAGE_MOUNT -lang $ISO_CODE >> $LOG_FILE
	else 
		/bin/echo "I'm running on Leopard. Checking for InstallerChoices.xml file" >> $LOG_FILE
			if [ -e ./BaseOS/InstallerChoices.xml ]
				then
				/bin/echo "InstallerChoices.xml file found. Applying Choices" >> $LOG_FILE
				/bin/echo "" >> $LOG_FILE
				/usr/sbin/installer -verbose -applyChoiceChangesXML ./InstallerChoices.xml -pkg "$CURRENT_OS_INSTALL_MOUNT/System/Installation/Packages/OSInstall.mpkg" -target $CURRENT_IMAGE_MOUNT -lang $ISO_CODE >> $LOG_FILE
				else
				/bin/echo "No InstallerChoices.xml file found. Installing full mpkg" >> $LOG_FILE
				/bin/echo "" >> $LOG_FILE
				/usr/sbin/installer -verbose -pkg "$CURRENT_OS_INSTALL_MOUNT/System/Installation/Packages/OSInstall.mpkg" -target $CURRENT_IMAGE_MOUNT -lang $ISO_CODE >> $LOG_FILE
			fi
		fi
		/bin/echo "" >> $LOG_FILE
		/bin/echo "" >> $PKG_LOG
		/bin/echo "Base OS installed" >> $LOG_FILE
		/bin/echo "Base OS installed" >> $PKG_LOG
		/bin/date +%H:%M:%S >> $LOG_FILE
		/bin/date +%H:%M:%S >> $PKG_LOG
		/bin/echo "" >> $LOG_FILE
		/bin/echo "" >> $LOG_FILE
		/bin/echo "" >> $PKG_LOG
		/bin/echo "" >> $PKG_LOG
}

# install packages from a folder of folders (01, 02, 03...etc)
install_packages_from_folder() {
	SELECTED_FOLDER="$1"
	
	/bin/date "+#####Beginning Update Installs from $SELECTED_FOLDER#####\n%H:%M:%S\n" | /usr/bin/tee -a "$LOG_FILE" "$PKG_LOG"

	if [ "$SELECTED_FOLDER" == "" ]; then
		/bin/echo "Error: install_packages_from_folder called without folder"
		exit 1;
	fi
	
	/bin/ls -A1 "$SELECTED_FOLDER" | /usr/bin/awk "/^[[:digit:]]+$/" | while read ORDERED_FOLDER
	do
		/bin/ls -A1 "$SELECTED_FOLDER/$ORDERED_FOLDER" | /usr/bin/awk 'tolower($1) ~ /\.(m)?pkg$/' | while read UPDATE_PKG
		do
			
			if [ -e "$SELECTED_FOLDER/$ORDERED_FOLDER/InstallerChoices.xml" ]; then
				CHOICES_FILE="InstallerChoices.xml"
				# TODO: better handle multiple pkg's and InstallerChoice files named for the file they should handle
			fi
			
			if [ "$OS_REV" -eq 0 ]; then
				CHOICES_FILE="" # 10.4 can not use them
			fi			
			
			if [ "$CHOICES_FILE" != "" ]; then
				/usr/sbin/installer -verbose -applyChoiceChangesXML "$SELECTED_FOLDER/$ORDERED_FOLDER/$CHOICES_FILE" -pkg "$SELECTED_FOLDER/$ORDERED_FOLDER/$UPDATE_PKG" -target "$CURRENT_IMAGE_MOUNT" | /usr/bin/tee -a "$LOG_FILE"
				/bin/echo "	Installed $SELECTED_FOLDER/$ORDERED_FOLDER/$UPDATE_PKG with XML Choices file: $CHOICES_FILE" | /usr/bin/tee -a "$LOG_FILE" "$PKG_LOG"
				
			else
				/usr/sbin/installer -verbose -pkg "$SELECTED_FOLDER/$ORDERED_FOLDER/$UPDATE_PKG" -target "$CURRENT_IMAGE_MOUNT" | /usr/bin/tee -a "$LOG_FILE"
				/bin/echo "	Installed $SELECTED_FOLDER/$ORDERED_FOLDER/$UPDATE_PKG" | /usr/bin/tee -a "$LOG_FILE" "$PKG_LOG"
			fi
		done
	done
}

# close up the DMG, compress and scan for restore
close_up_and_compress() {
	/bin/echo "#####Creating the deployment DMG and scanning for ASR#####" >> $LOG_FILE
	/bin/date +%H:%M:%S >> $LOG_FILE
	/bin/echo "" >> $LOG_FILE
	
	# We'll rename the newly installed system to make it easier to work with later
	/bin/echo "Rename the deployment volume" >> $LOG_FILE
	#/usr/sbin/diskutil "rename $CURRENT_IMAGE_MOUNT $ASR_FS_NAME" >> $LOG_FILE
	#CURRENT_IMAGE_MOUNT=/Volumes/$ASR_FS_NAME

	/usr/sbin/diskutil rename $CURRENT_IMAGE_MOUNT OS-Build-${CREATE_DATE} >> $LOG_FILE
	CURRENT_IMAGE_MOUNT=/Volumes/OS-Build-${CREATE_DATE}
	/bin/echo "New ASR source volume name is " $CURRENT_IMAGE_MOUNT >> $LOG_FILE
	/bin/echo "" >> $LOG_FILE

	# Create a new, compessed, image from the intermediary one and scan for ASR.
	/bin/echo "Build a new image from folder..." >> $LOG_FILE
	/bin/date +%H:%M:%S >> $LOG_FILE
	/usr/bin/hdiutil create -format UDZO -imagekey zlib-level=6 -srcfolder $CURRENT_IMAGE_MOUNT  ${ASR_FOLDER}/${CREATE_DATE} >> $LOG_FILE
	/bin/echo "New image created..." >> $LOG_FILE
	/bin/date +%H:%M:%S >> $LOG_FILE
	/bin/echo "" >> $LOG_FILE
	/bin/echo "Scanning image for ASR" >> $LOG_FILE
	/bin/echo "Image to scan is ${ASR_FOLDER}/${CREATE_DATE}.dmg" >> $LOG_FILE
	/usr/sbin/asr imagescan --verbose --source ${ASR_FOLDER}/${CREATE_DATE}.dmg 2>&1 >> $LOG_FILE
	
	/bin/echo "" >> $LOG_FILE
	/bin/date +%H:%M:%S >> $LOG_FILE
	/bin/echo "ASR image scan complete" >> $LOG_FILE
	/bin/echo "" >> $LOG_FILE
	/bin/echo "" >> $LOG_FILE
}

# restore DMG to test partition
restore_image() {
	/bin/echo "#####Restoring ASR image to test partition#####" >> $LOG_FILE
	/bin/date +%H:%M:%S >> $LOG_FILE
	/usr/sbin/asr "--verbose --source ${ASR_FOLDER}/${CREATE_DATE}.dmg --target $ASR_TARGET_VOLUME --erase --nocheck --noprompt" >> $LOG_FILE
	/bin/echo "ASR image restored..." >> $LOG_FILE
	/bin/date +%H:%M:%S >> $LOG_FILE
	/bin/echo "" >> $LOG_FILE
	/bin/echo "" >> $LOG_FILE
}

# set test partition to be the boot partition
set_boot_test() {
	/bin/echo "#####Blessing test partition#####" >> $LOG_FILE
	/bin/date +%H:%M:%S >> $LOG_FILE
	/usr/sbin/bless "--mount $CURRENT_IMAGE_MOUNT --setBoot" >> $LOG_FILE
	/bin/echo "Test partition blessed" >> $LOG_FILE
	/bin/echo "" >> $LOG_FILE
	/bin/echo "" >> $LOG_FILE
}

# clean up
clean_up() {
	/bin/echo "#####Cleaning up#####" >> $LOG_FILE
	/bin/date +%H:%M:%S >> $LOG_FILE
	/bin/echo "Ejecting images" >> $LOG_FILE
	/usr/sbin/diskutil eject $CURRENT_IMAGE_MOUNT_DEV >> $LOG_FILE
	/usr/sbin/diskutil eject $CURRENT_OS_INSTALL_MOUNT >> $LOG_FILE
	/bin/echo "Removing scratch DMG" >> $LOG_FILE
	/bin/echo "" >> $LOG_FILE
	/bin/rm ./DMG_Scratch/* 2>&1 >> $LOG_FILE
	/bin/echo "" >> $LOG_FILE
	
}

# reboot the Mac
reboot() {
	/bin/echo "#####Restarting#####" >> $LOG_FILE
	/bin/date +%H:%M:%S >> $LOG_FILE
	/sbin/shutdown -r +1
}

# Timestamp the end of the build train.
timestamp() {
	/bin/echo $CREATE_DATE >> $LOG_FILE
	/bin/date +%H:%M:%S >> $LOG_FILE
	/bin/echo $CREATE_DATE >> $PKG_LOG
	/bin/date +%H:%M:%S >> $PKG_LOG
	/bin/echo "InstaDMG Complete" >> $LOG_FILE
	/bin/echo "#############################################################" >> $LOG_FILE
	/bin/echo "InstaDMG Complete" >> $PKG_LOG
	/bin/echo "#############################################################" >> $PKG_LOG
}

# Call the handlers as needed to make it all happen.
check_root
create_and_mount_image
mount_os_install
install_system
install_packages_from_folder "$UPDATE_FOLDER"
install_packages_from_folder "$CUSTOM_FOLDER"
close_up_and_compress
clean_up
timestamp

# Automated restore options. Be careful as these can destroy data.
# restore_image
# set_boot_test
# reboot

exit 0
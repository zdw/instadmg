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
	/bin/ls -A1 $INSTALLER_FOLDER | /usr/bin/sed '/.DS_Store/d' | /usr/bin/sed '/InstallerChoices.xml/d'| while read i
	do
	 /usr/bin/hdiutil mount "$INSTALLER_FOLDER/$i" >> $LOG_FILE
	done
	if [ -d /Volumes/Mac\ OS\ X\ Install\ Disc\ 1 ]
		then
		CURRENT_OS_INSTALL_MOUNT="/Volumes/Mac OS X Install Disc 1"
		else
			if [ -d /Volumes/Mac\ OS\ X\ Server\ Install\ Disc ]
				then
				CURRENT_OS_INSTALL_MOUNT="/Volumes/Mac OS X Server Install Disc"
				SERVER_INSTALL="1"
				else
			CURRENT_OS_INSTALL_MOUNT="/Volumes/Mac OS X Install DVD"
			fi
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

# install the updates to the DMG
install_updates() {
	/bin/echo "#####Beginning Baseload update Installs from $UPDATE_FOLDER#####" >> $LOG_FILE
	/bin/echo "#####Beginning Baseload update Installs from $UPDATE_FOLDER#####" >> $PKG_LOG
	/bin/date +%H:%M:%S >> $LOG_FILE
	/bin/date +%H:%M:%S >> $PKG_LOG
	/bin/echo "" >> $LOG_FILE
	/bin/echo "" >> $PKG_LOG
	
	/bin/ls -A1 $UPDATE_FOLDER | /usr/bin/sed '/.DS_Store/d' | while read UPDATE_PKG
		do
		if [ -e $UPDATE_FOLDER/$UPDATE_PKG/InstallerChoices.xml ]
		then
			/usr/sbin/installer -verbose -applyChoiceChangesXML $UPDATE_FOLDER/$UPDATE_PKG/InstallerChoices.xml -pkg "${UPDATE_FOLDER}/${UPDATE_PKG}/`/bin/ls ${UPDATE_FOLDER}/${UPDATE_PKG} | /usr/bin/sed -e '/.DS_Store/d' -e '/InstallerChoices.xml/d'`" -target $CURRENT_IMAGE_MOUNT >> $LOG_FILE
			/bin/echo "Installed ${UPDATE_FOLDER}/${UPDATE_PKG}/`/bin/ls ${UPDATE_FOLDER}/${UPDATE_PKG} | /usr/bin/sed -e '/.DS_Store/d' -e '/InstallerChoices.xml/d'` with installer choices." >> $PKG_LOG
		else
			/usr/sbin/installer -verbose -pkg "${UPDATE_FOLDER}/${UPDATE_PKG}/`/bin/ls ${UPDATE_FOLDER}/${UPDATE_PKG} | /usr/bin/sed '/.DS_Store/d'`" -target $CURRENT_IMAGE_MOUNT >> $LOG_FILE
			/bin/echo "Installed ${UPDATE_FOLDER}/${UPDATE_PKG}/`/bin/ls ${UPDATE_FOLDER}/${UPDATE_PKG} | /usr/bin/sed '/.DS_Store/d'`" >> $PKG_LOG
		fi
	done
	/bin/echo "" >> $LOG_FILE
	/bin/echo "" >> $PKG_LOG
	/bin/echo "Baseload updates installed" >> $LOG_FILE
	/bin/echo "Baseload updates installed" >> $PKG_LOG
	/bin/date +%H:%M:%S >> $LOG_FILE
	/bin/date +%H:%M:%S >> $PKG_LOG
	/bin/echo "" >> $LOG_FILE
	/bin/echo "" >> $LOG_FILE
	/bin/echo "" >> $PKG_LOG
	/bin/echo "" >> $PKG_LOG
}

# install the custom pieces to the DMG
install_custom() {
	/bin/echo "#####Beginning Update Installs from $CUSTOM_FOLDER#####" >> $LOG_FILE
	/bin/echo "#####Beginning Update Installs from $CUSTOM_FOLDER#####" >> $PKG_LOG
	/bin/date +%H:%M:%S >> $LOG_FILE
	/bin/date +%H:%M:%S >> $PKG_LOG
	/bin/echo "" >> $LOG_FILE
	/bin/echo "" >> $PKG_LOG
	
	/bin/ls -A1 $CUSTOM_FOLDER | /usr/bin/sed '/.DS_Store/d' | while read CUSTOM_PKG
		do
		if [ -e $CUSTOM_FOLDER/$CUSTOM_PKG/InstallerChoices.xml ]
		then
			/usr/sbin/installer -verbose -applyChoiceChangesXML "${CUSTOM_FOLDER}/${CUSTOM_PKG}/InstallerChoices.xml" -pkg "${CUSTOM_FOLDER}/${CUSTOM_PKG}/`/bin/ls ${CUSTOM_FOLDER}/${CUSTOM_PKG} | /usr/bin/sed -e '/.DS_Store/d' -e '/InstallerChoices.xml/d'`" -target $CURRENT_IMAGE_MOUNT >> $LOG_FILE
			/bin/echo "Installed ${CUSTOM_FOLDER}/${CUSTOM_PKG}/`/bin/ls ${CUSTOM_FOLDER}/${CUSTOM_PKG} | /usr/bin/sed -e '/.DS_Store/d' -e '/InstallerChoices.xml/d'`" >> $PKG_LOG
		else
			/usr/sbin/installer -verbose -pkg "${CUSTOM_FOLDER}/${CUSTOM_PKG}/`/bin/ls ${CUSTOM_FOLDER}/${CUSTOM_PKG} | /usr/bin/sed '/.DS_Store/d'`" -target $CURRENT_IMAGE_MOUNT >> $LOG_FILE
			/bin/echo "Installed ${CUSTOM_FOLDER}/${CUSTOM_PKG}/`/bin/ls ${CUSTOM_FOLDER}/${CUSTOM_PKG} | /usr/bin/sed '/.DS_Store/d'`" >> $PKG_LOG
		fi
	done
	/bin/echo "" >> $LOG_FILE
	/bin/echo "" >> $PKG_LOG
	/bin/echo "Custom packages installed" >> $LOG_FILE
	/bin/echo "Custom packages installed" >> $PKG_LOG
	/bin/date +%H:%M:%S >> $LOG_FILE
	/bin/date +%H:%M:%S >> $PKG_LOG
	/bin/echo "" >> $LOG_FILE
	/bin/echo "" >> $LOG_FILE
	/bin/echo "" >> $PKG_LOG
	/bin/echo "" >> $PKG_LOG
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
install_updates
install_custom
close_up_and_compress
clean_up
timestamp

# Automated restore options. Be careful as these can destroy data.
# restore_image
# set_boot_test
# reboot

exit 0
#!/bin/bash
#
# instadmg - script to automate creating ASR disk images
#
#
#  Joel Rennich - mactroll@afp548.com - SFO -> ORD
#  Josh Wisenbaker - macshome@afp548.com - CLT -> LAX (Among many others...)
#
# Version 1.0
#
# some defaults to get us started
#
################################################################################
#                                 Configuration                                #
################################################################################
# Set For HardDisk Install
	# /Volumes is assumed ?
	DEST_HARDDISK_VOL="InstallDisk"
# Values 1=yes, 0=no
	HARDDISK=0
# Verbose flags enabled - values 1=yes, 0=no
	VERBOSITY=1
# Install from ASR Image - values 1=yes, 0=no
	INSTALL_ASR=1
# ASR Image Name
	ASR_SOURCE_FILE="07-10-15-leopard-base.dmg"
# Working Volume
	WORKING_VOLUME=/Volumes/UserSpace/InstaDMG
#	WORKING_VOLUME=/Volumes/MirrorHD/ISO
# This string is the root of the scratch image name.
	DMG_BASE_NAME="InstaDMG"
# This string is the root filesystem name for the ASR image to be restored.
	DMG_FS_NAME="InstaDMG"
# Default scratch image size. It should not need adjustment.
	DMG_SIZE="300g"
# ASR target volume. Make sure you set it to the correct thing! In a future release this, and most variables, will be a getopts parameter.
	TARGET_VOLUME=/Volumes/foo
# Destination Platform
	PLATFORM="PPC"
	#PLATFORM="INTEL"
#
################################################################################
#                             END USER  CONFIGURATION                          #
################################################################################
# Do not change anything below this line

# Some shell variables we need
#
export COMMAND_LINE_INSTALL=1
#=======================================================
################################################################################
#                           Define Functions                                   #
################################################################################
#
# Now for the meat
#
### check_root #################################################################
# check to make sure we are root, can't do these things otherwise
check_root() {
    if [ `whoami` != "root" ]
    then
        $ECHO "you need to be root to do this"
        exit 0;
    fi
}
### testkit ####################################################################
# This function tests the binaries used in this program and if all are valid, 
# the program will run
function testkit () {
	if [ $ALLDONE -eq 0 ]; then
		command_test=$(/usr/bin/whatis $1 | /usr/bin/grep 'nothing appropriate')
		if [  -z "$command_test" ]; then
			ALLDONE=0
			return 0
		else
			ALLDONE=1
			return 1
		fi
	else
		ALLDONE=1
		return 1
	fi
}
### erase_disk_PPC #############################################################
# setup and create the DMG. Uncomment and comment the reformatting based on your platform. This will be automated in a future release.

erase_disk_PPC() {
	$ECHO "Erasing Disk for PPC Platform" >> $LOG_FILE
	$ECHO "Formatting as $DMG_FS_NAME at $CURRENT_IMAGE_MOUNT_DEV" >> $LOG_FILE
	if [ $HARDDISK -eq 1 ]; then
		$ECHO "Formatting as Hard Disk" >> $LOG_FILE
		$DISKUTIL eraseVolume JHFS+ $DMG_FS_NAME bootable $CURRENT_IMAGE_MOUNT_DEV >> $LOG_FILE
	else
		$ECHO "Formatting as Disk Image" >> $LOG_FILE
		$DISKUTIL eraseDisk JHFS+ $DMG_FS_NAME bootable $CURRENT_IMAGE_MOUNT_DEV >> $LOG_FILE
	fi
}
### erase_disk_Intel ###########################################################
erase_disk_Intel() {
	$ECHO "Erasing Disk for Intel Platform" >> $LOG_FILE
	$ECHO "Formatting as $DMG_FS_NAME at $CURRENT_IMAGE_MOUNT_DEV" >> $LOG_FILE
	if [ $HARDDISK -eq 1 ]; then
		$ECHO "Formatting as Hard Disk" >> $LOG_FILE
		$DISKUTIL eraseVolume JHFS+ $DMG_FS_NAME bootable $CURRENT_IMAGE_MOUNT_DEV >> $LOG_FILE
	else
		$ECHO "Formatting as Disk Image" >> $LOG_FILE
		$DISKUTIL eraseDisk JHFS+ $DMG_FS_NAME bootable $CURRENT_IMAGE_MOUNT_DEV >> $LOG_FILE
	fi
}
### erase_disk_Platform ########################################################
erase_disk_platform() {
	if [ $PLATFORM = "PPC" ]; then
		erase_disk_PPC
	else
		erase_disk_Intel
	fi
}
### create_and_mount_image_new #################################################
# setup and create the DMG. Uncomment and comment the reformatting based on your platform. This will be automated in a future release.
create_and_mount_image_new() {
	$ECHO $CREATE_DATE >> $LOG_FILE

# Test - Are we installing to an image or a physical drive
	if [ $HARDDISK -eq 1 ]; then
		DMG_FS_NAME=$DEST_HARDDISK_VOL
		CURRENT_IMAGE_MOUNT_DEV=`$DF | $GREP $DEST_HARDDISK_VOL | $HEAD -n 1 | $AWK '{ print $1 }'`
		$HDIUTIL unmount $CURRENT_IMAGE_MOUNT_DEV -force >> $LOG_FILE
	else
		$ECHO "Creating disk image" >> $LOG_FILE
		[ -e ${DMG_BASE_NAME}.${CREATE_DATE}.sparseimage ] && $CREATE_DATE
		$HDIUTIL create \
			-autostretch \
			-type SPARSE \
			-fs HFS+ \
			$DMG_SCRATCH/${DMG_BASE_NAME}.${CREATE_DATE} \
			-volname $DMG_FS_NAME \
			-ov \
			-layout "UNIVERSAL HD" >> $LOG_FILE
		CURRENT_IMAGE_MOUNT_DEV=`$HDIUTIL attach $DMG_SCRATCH/${DMG_BASE_NAME}.${CREATE_DATE}.sparseimage -noverify  | $HEAD -n 1 |  $AWK '{ print $1 }'`
		$ECHO "Image mounted at $CURRENT_IMAGE_MOUNT_DEV" >> $LOG_FILE
		$ECHO $CURRENT_IMAGE_MOUNT_DEV >> $DMG_SCRATCH/dev_file.dat
	fi
	# Destination CPU Type - What kind of disk are you burning
	cpu_type=$($SYSCTL hw.machine | $GREP -c i386)
	if [ $cpu_type -eq 0 ]; then 
		$ECHO "I'm Running on PPC Platform" >> $LOG_FILE
	else 
		$ECHO "I'm Running on Intel Platform" >> $LOG_FILE
	fi
	erase_disk_platform
$ECHO "Formatting as Disk Image at $DMG_FS_NAME on $CURRENT_IMAGE_MOUNT_DEV" >> $LOG_FILE

	CURRENT_IMAGE_MOUNT=/Volumes/$DMG_FS_NAME
	$ECHO "Current Image Mount is $CURRENT_IMAGE_MOUNT" >> $LOG_FILE
}

# Mount the OS source image.
# If you have some wacky disk name then change this as needed.
### mount_os_install_new #######################################################
mount_os_install_new() {
		if [ -d /Volumes/Mac\ OS\ X\ Install\ DVD ]; then
			CURRENT_OS_INSTALL_MOUNT="/Volumes/Mac OS X Install DVD"
		else
			$LS -1 $INSTALLER_FOLDER | while read i
			do
				if [ $i != ".DS_Store" ]; then
					OS_INSTALL_MOUNT_POINT=`$HDIUTIL attach "$INSTALLER_FOLDER/$i" -noverify | $HEAD -n 1 |  $AWK '{ print $1 }'`
					$ECHO $OS_INSTALL_MOUNT_POINT >> $DMG_SCRATCH/dev_file.dat
					$ECHO $OS_INSTALL_MOUNT_POINT >> $LOG_FILE		
				fi
			done
			if [ -d /Volumes/Mac\ OS\ X\ Install\ Disc\ 1 ]; then
				CURRENT_OS_INSTALL_MOUNT="/Volumes/Mac OS X Install Disc 1"
			else
				CURRENT_OS_INSTALL_MOUNT="/Volumes/Mac OS X Install DVD"
			fi
		fi
}
### install_system_new #########################################################
# Install from installation media to the DMG
# The default is to install with english as the primary.
# Change to your ISO code as needed.

install_system_new() {
	if [ $INSTALL_ASR -eq 0 ]; then
		mount_os_install_new
		$ECHO $CREATE_DATE >> $LOG_FILE
		$ECHO $CREATE_DATE >> $PKG_LOG
		$ECHO "Beginning Installation from $CURRENT_OS_INSTALL_MOUNT" >> $LOG_FILE
		$ECHO "Beginning Installation from $CURRENT_OS_INSTALL_MOUNT" >> $PKG_LOG
# for more detailed logs
		if [ $VERBOSITY -eq 1 ]; then
			$INSTALLER \
				-verbose \
				-pkg "$CURRENT_OS_INSTALL_MOUNT/System/Installation/Packages/OSInstall.mpkg" \
				-target $CURRENT_IMAGE_MOUNT \
				-lang en >> $LOG_FILE
		else
			$INSTALLER \
				-pkg "$CURRENT_OS_INSTALL_MOUNT/System/Installation/Packages/OSInstall.mpkg" \
				-target $CURRENT_IMAGE_MOUNT \
				-lang en >> $LOG_FILE
		fi
	else
		$ASR --source ${ASR_FOLDER}/$ASR_SOURCE_FILE \
			--target $CURRENT_IMAGE_MOUNT \
			--noverify \
			--noprompt \
			--verbose >> $LOG_FILE
#testing w/out the --erase option			
			CURRENT_IMAGE_MOUNT_DEV=$($HDIUTIL attach $DMG_SCRATCH/$DMG_BASE_NAME.$CREATE_DATE.sparseimage -noverify  | $HEAD -n 1 |  $AWK '{ print $1 }')
			$DISKUTIL rename $CURRENT_IMAGE_MOUNT_DEV $DMG_FS_NAME
			$ECHO "Current state $CURRENT_IMAGE_MOUNT_DEV $DMG_FS_NAME $CURRENT_IMAGE_MOUNT"
	fi
}
### install_updates ############################################################
# install the updates to the DMG
install_updates() {
	$ECHO $CREATE_DATE >> $LOG_FILE
	$ECHO $CREATE_DATE >> $PKG_LOG
	$ECHO "Beginning Update Installs from $UPDATE_FOLDER" >> $LOG_FILE
	$ECHO "Beginning Update Installs from $UPDATE_FOLDER" >> $PKG_LOG
	
	for UPDATE_PKG in `$LS $UPDATE_FOLDER`
		do
		if [ $UPDATE_PKG = ".DS_Store" ]; then
			$ECHO "Skipping .ds_store file" >> $LOG_FILE
		else
			if [ $VERBOSITY -eq 1 ]; then
				$INSTALLER \
					-verbose \
					-pkg ${UPDATE_FOLDER}/${UPDATE_PKG} \
					-target $CURRENT_IMAGE_MOUNT >> $LOG_FILE
			else
				$INSTALLER \
				-pkg ${UPDATE_FOLDER}/${UPDATE_PKG} \
				-target $CURRENT_IMAGE_MOUNT >> $LOG_FILE
			fi
			$ECHO "Installed $UPDATE_PKG" >> $PKG_LOG
		fi
	done
}
### install_custom #############################################################
# install the custom pieces to the DMG
install_custom() {
	$ECHO $CREATE_DATE >> $LOG_FILE
	$ECHO $CREATE_DATE >> $PKG_LOG
	$ECHO "Beginning Update Installs from $CUSTOM_FOLDER" >> $LOG_FILE
	$ECHO "Beginning Update Installs from $CUSTOM_FOLDER" >> $PKG_LOG
	
	for CUSTOM_PKG in `$LS $CUSTOM_FOLDER`
		do
		if [ $CUSTOM_PKG = ".DS_Store" ]; then
			$ECHO "Skipping .ds_store file" >> $LOG_FILE
		else
			if [ $VERBOSITY -eq 1 ]; then
				$INSTALLER \
					-verbose \
					-pkg ${CUSTOM_FOLDER}/${CUSTOM_PKG} \
					-target $CURRENT_IMAGE_MOUNT >> $LOG_FILE
			else
				$INSTALLER \
					-pkg ${CUSTOM_FOLDER}/${CUSTOM_PKG} \
					-target $CURRENT_IMAGE_MOUNT >> $LOG_FILE
			fi	
			$ECHO "Installed $CUSTOM_PKG" >> $PKG_LOG
		fi
	done
}
### close_up_and_compress ######################################################
# close up the DMG, compress and scan for restore
close_up_and_compress() {
	$ECHO $CREATE_DATE >> $LOG_FILE
	$ECHO "Creating the deployment DMG and scanning for ASR" >> $LOG_FILE
	
# We'll rename the newly installed system to make it easier to work with later
	$ECHO "Rename the deployment volume $CURRENT_IMAGE_MOUNT" >> $LOG_FILE

	$DISKUTIL rename $CURRENT_IMAGE_MOUNT OS-Build-${CREATE_DATE} >> $LOG_FILE
	CURRENT_IMAGE_MOUNT=/Volumes/OS-Build-${CREATE_DATE}
	
	$ECHO "Build a new image from folder $CURRENT_IMAGE_MOUNT ..." >> $LOG_FILE
	$HDIUTIL create \
		-ov \
		-format UDZO \
		-imagekey zlib-level=6 \
		-srcfolder $CURRENT_IMAGE_MOUNT  \
		${ASR_FOLDER}/${CREATE_DATE} >> $LOG_FILE

	if [ $HARDDISK -eq 1 ]; then
		$ECHO "We Will not UnMount a Hard Disk on exit" >> $LOG_FILE
	else
		$ECHO "attempting to unmount image at $CURRENT_IMAGE_MOUNT_DEV" >> $LOG_FILE
		$HDIUTIL detach $CURRENT_IMAGE_MOUNT_DEV -force >> $LOG_FILE
	fi
	$ECHO "Scanning image for ASR" >> $LOG_FILE
	$ECHO "Image to scan is ${ASR_FOLDER}/${CREATE_DATE}.dmg" >> $LOG_FILE
	$ASR imagescan --source ${ASR_FOLDER}/${CREATE_DATE}.dmg >> $LOG_FILE
}
### restore_image ##############################################################
# restore DMG to test partition
restore_image() {
	$ASR --source ${ASR_FOLDER}/${CREATE_DATE}.dmg \
		--target $TARGET_VOLUME \
		--erase \
		--noverify \
		--noprompt >> $LOG_FILE
}
### set_boot_test ##############################################################
# set test partition to be the boot partition
set_boot_test() {
	$BLESS --mount /Volumes/OS-Build-${CURRENT_DATE} --setBoot
}
### clean_up ###################################################################
clean_up() {
	$ECHO "ejecting media" >> $LOG_FILE
	$CAT $DMG_SCRATCH/dev_file.dat | while read i
	do
		$HDIUTIL detach $i -force >> $LOG_FILE
	done
	$ECHO "Removing Scratch files" >> $LOG_FILE
	$RM $DMG_SCRATCH/*
}
### reboot #####################################################################
# reboot the Mac
reboot() {
	$SHUTDOWN -r +1
}
################################################################################
#                           End Functions                                      #
################################################################################
################################################################################
#                           Define Variables and Command Kit                   #
################################################################################
# Let's build and check our command kit
# These are the Commands we want to use - 
# the (which xxx) returns the full path to the executable
#
# here we test to see if the executable actually will execute for our user credentials
ALLDONE=0
# since all of the definitions are not complete - the first call is done manually
testkit which $ALLDONE		&& [[ $ALLDONE -eq 0 ]] && WHICH=$(/usr/bin/which which)
testkit echo $ALLDONE		&& [[ $ALLDONE -eq 0 ]] && ECHO=$($WHICH echo)
testkit date $ALLDONE		&& [[ $ALLDONE -eq 0 ]] && DATE=$($WHICH date)
testkit diskutil $ALLDONE		&& [[ $ALLDONE -eq 0 ]] && DISKUTIL=$($WHICH diskutil)
testkit df $ALLDONE			&& [[ $ALLDONE -eq 0 ]] && DF=$($WHICH df)
testkit grep $ALLDONE		&& [[ $ALLDONE -eq 0 ]] && GREP=$($WHICH grep)
testkit head $ALLDONE		&& [[ $ALLDONE -eq 0 ]] && HEAD=$($WHICH head)
testkit awk $ALLDONE		&& [[ $ALLDONE -eq 0 ]] && AWK=$($WHICH awk)
testkit hdiutil $ALLDONE	&& [[ $ALLDONE -eq 0 ]] && HDIUTIL=$($WHICH hdiutil)
testkit sysctl $ALLDONE	&& [[ $ALLDONE -eq 0 ]] && SYSCTL=$($WHICH sysctl)
testkit ls $ALLDONE			&& [[ $ALLDONE -eq 0 ]] && LS=$($WHICH ls)
testkit installer $ALLDONE			&& [[ $ALLDONE -eq 0 ]] && INSTALLER=$($WHICH installer)
testkit asr $ALLDONE			&& [[ $ALLDONE -eq 0 ]] && ASR=$($WHICH asr)
testkit bless $ALLDONE			&& [[ $ALLDONE -eq 0 ]] && BLESS=$($WHICH bless)
testkit cat $ALLDONE		&& [[ $ALLDONE -eq 0 ]] && CAT=$($WHICH cat)
testkit rm $ALLDONE			&& [[ $ALLDONE -eq 0 ]] && RM=$($WHICH rm)
testkit shutdown $ALLDONE			&& [[ $ALLDONE -eq 0 ]] && SHUTDOWN=$($WHICH shutdown)

# Set the creation date in a variable so it's consistant during execution.
	CREATE_DATE=`$DATE +%y-%m-%d`
# Put images of your install DVDs in here
	INSTALLER_FOLDER=$WORKING_VOLUME/BaseOS
# Put naked Apple pkg updates in here. Prefix a number to order them.
	UPDATE_FOLDER=$WORKING_VOLUME/AppleUpdates
# Put naked custom pkg installers here. Prefix a number to order them.
	CUSTOM_FOLDER=$WORKING_VOLUME/CustomPKG
# This is the final ASR destination for the image.
	ASR_FOLDER=$WORKING_VOLUME/ASR_Output
# This is where DMG scratch is done. Set this to whatever you want.
	DMG_SCRATCH=$WORKING_VOLUME/DMG_Scratch
# Default log location.
	LOG_FOLDER=$WORKING_VOLUME/Logs
# Default log names. The PKG log is a more consise history of what was installed.
	LOG_FILE=$LOG_FOLDER/$CREATE_DATE.log
	PKG_LOG=$LOG_FOLDER/$CREATE_DATE.pkg.log


################################################################################
#                           End Definitions                                    #
################################################################################
################################################################################
#                           Begin Program                                      #
################################################################################
# Call the handlers as needed to make it all happen.

if [ $ALLDONE -eq 0 ]; then
	$ECHO "---- starting ----" >> $LOG_FILE
	$ECHO `$DATE "+DATE: %m/%d/%y%nTIME: %H:%M:%S"` >> $LOG_FILE
		create_and_mount_image_new
	$ECHO "---- completed part 1 - create_and_mount_image_new ----" >> $LOG_FILE
#		mount_os_install_new 
#		moved into step 3
	$ECHO "---- completed part 2 - mount_os_install_new ----" >> $LOG_FILE
		install_system_new
	$ECHO "---- completed part 3 - install_system_new ----" >> $LOG_FILE
		install_updates
	$ECHO "---- completed part 4 - install_updates ----" >> $LOG_FILE
		install_custom
	$ECHO "---- completed part 5 - install_custom ----" >> $LOG_FILE
		close_up_and_compress
	$ECHO "---- completed part 6 - close_up_and_compress ----" >> $LOG_FILE
		clean_up
	$ECHO "---- completed part 7 - clean_up ----" >> $LOG_FILE
	$ECHO `$DATE "+DATE: %m/%d/%y%nTIME: %H:%M:%S"` >> $LOG_FILE
	$ECHO "---- Program End ----" >> $LOG_FILE

# Automated restore options. Be careful as these can destroy data.
# restore_image
# set_boot_test
# reboot

else
	$ECHO "Error Encountered in Defining Variables and command sets" >> $LOGFILE
fi	

exit 0
################################################################################
#                           End Program                                        #
################################################################################

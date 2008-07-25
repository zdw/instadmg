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

VERSION="1.4b1"
PROGRAM=$( (basename $0) )

# Set the creation date in a variable so it's consistant during execution.
CREATE_DATE=`date +%y-%m-%d`

# Am I running on Leopard? This will equal 1 on 10.5 and 0 on everything else.
OS_REV=`/usr/bin/sw_vers | /usr/bin/grep -c 10.5`

# CPU type of the Mac running InstaDMG. If we are on Intel this will equal 1. Otherwise it equals 0.
CPU_TYPE=`arch | /usr/bin/grep -c i386`

# Default ISO code for default install language. Script default is English.
#ISO_CODE="en"

# Are we installing Mac OS X . This defaults to 0 for no.
#SERVER_INSTALL="0"

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

bail()
{	
	#If we get here theres a problem, print the usage message and then exit with a non-zero status
	
	usage
	exit $1
}

version()
{

# Show the version number

	echo "$PROGRAM version $VERSION"
}

usage()
{

# Usage format

cat <<EOF
Usage:  $PROGRAM
	[ -h "Help about this utility"]
	[ -v "Version number"]
	[ -s "Server install"]
 	[ -l "Language"]
	[ -i "Install folder"]
	[ -u "Update folder"]
	[ -c "Custom folder"]
	[ -a "ASR output folder"]
	[ -d "DMG Scratch folder"]
	[ -l "Log Folder"]
	[ -q "Quiet mode"]
EOF
}

log()
{
if [ "$1" = "" ]
	then
	printf "$(date +%H:%M:%S )\n"
	else
	printf "$1\n"
fi
}

rootcheck()
{

# Root is required to run instadmg

echo "Warning:  You must run this utility using sudo or as root!"
exit 64

}

# check to make sure we are root, can't do these things otherwise

#check_root() {
#    if [ `whoami` != "root" ]
#    then
#        log "you need to be root to do this so use sudo"
#        exit 0;
#    fi
#}

# setup and create the DMG.

create_and_mount_image() {
	log "#############################################################" 
	log "InstaDMG build initiated" 
	log "#############################################################" >&4
	log "InstaDMG build initiated" >&4
	printf "\n" 
	log $CREATE_DATE 
	printf "\n" 
	printf "\n" >&4
	log "####Creating intermediary disk image#####" 
	log 
	printf "\n" 
	[ -e ${DMG_BASE_NAME}.${CREATE_DATE}.sparseimage ] && $CREATE_DATE		
	/usr/bin/hdiutil create -size $DMG_SIZE -type SPARSE -fs HFS+ $DMG_SCRATCH/${DMG_BASE_NAME}.${CREATE_DATE} 
	CURRENT_IMAGE_MOUNT_DEV=`/usr/bin/hdiutil attach $DMG_SCRATCH/$DMG_BASE_NAME.$CREATE_DATE.sparseimage | /usr/bin/head -n 1 |  /usr/bin/awk '{ print $1 }'`
	log "Image mounted at $CURRENT_IMAGE_MOUNT_DEV" 
	printf "\n" 
	
	# Format the DMG so that the Installer will like it 

	# Determine the platform
		if [ $CPU_TYPE -eq 0 ]; then 
			log "I'm Running on PPC Platform" 
			log "Setting format to APM" 
			printf "\n" 
			
			#(PPC Mac)
				/usr/sbin/diskutil eraseDisk "Journaled HFS+" $DMG_BASE_NAME APMformat $CURRENT_IMAGE_MOUNT_DEV 
				printf "\n" 
				CURRENT_IMAGE_MOUNT=/Volumes/$DMG_BASE_NAME
		else 
			log "I'm Running on Intel Platform" 
			log "Setting format to GPT" 
			printf "\n" 
			#(Intel Mac)
				/usr/sbin/diskutil eraseDisk "Journaled HFS+" $DMG_BASE_NAME GPTFormat $CURRENT_IMAGE_MOUNT_DEV 
				printf "\n" 
				CURRENT_IMAGE_MOUNT=/Volumes/$DMG_BASE_NAME
		fi
		log "Intimediary image creation complete" 
		log 
		printf "\n" 
		printf "\n" 
}

# Mount the OS source image.
# If you have some wacky disk name then change this as needed.

mount_os_install() {
	log "#####Mounting Mac OS X installer image#####" 
	log 
	printf "\n" 
	
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
				if [ `log "$HDIUTIL_LINE" | /usr/bin/grep -c '================================================'` -eq 1 ]; then
					# this is the marker for a new section, so we need to clear things out
					IMAGE_LOCATION=""
					MOUNTED_IMAGES=""
			
				elif [ "`log "$HDIUTIL_LINE" | /usr/bin/awk '/^image-path/'`" != "" ]; then
					IMAGE_LOCATION=`log "$HDIUTIL_LINE" | /usr/bin/awk 'sub("^image-path[[:space:]]+:[[:space:]]+", "")'`
					
					# check the inodes to see if we are pointing at the same file
					if [ "`/bin/ls -Li "$IMAGE_LOCATION" | awk '{ print $1 }'`" != "`/bin/ls -Li "$IMAGE_FILE" | awk '{ print $1 }'`" ]; then
						# this is not the droid we are looking for
						IMAGE_LOCATION=""
						
						# if it is the same thing, then we let it through to get the mount point below
					fi
				elif [ "$IMAGE_LOCATION" != "" ] && [ "`log "$HDIUTIL_LINE" | /usr/bin/awk '/\/dev\/.+[[:space:]]+Apple_HFS[[:space:]]+\//'`" != "" ]; then
					# find the mount point
					CURRENT_OS_INSTALL_MOUNT=`log "$HDIUTIL_LINE" | /usr/bin/awk 'sub("/dev/.+[[:space:]]+Apple_HFS[[:space:]]+", "")'`
					`log "$CURRENT_OS_INSTALL_MOUNT" > "$TEMPFILE"` # to get around bash variable scope difficulties
					# Here we are done!
					log "	The main OS Installer Disk was already mounted at: $CURRENT_OS_INSTALL_MOUNT" 
				fi
			done
			
			if [ "$CURRENT_OS_INSTALL_MOUNT" == "" ]; then
				# since it was not already mounted, we have to mount it
				#	we are going to mount it non-browsable, so it does not appear in the finder, and we are going to mount it to a temp folder
				
				CURRENT_OS_INSTALL_MOUNT=`/usr/bin/mktemp -d /tmp/instaDMGMount.XXXXXX`
				log "	Mounting the main OS Installer Disk from: $IMAGE_FILE at: $CURRENT_OS_INSTALL_MOUNT" 
				/usr/bin/hdiutil mount "$IMAGE_FILE" -readonly -nobrowse -mountpoint "$CURRENT_OS_INSTALL_MOUNT" 
				`log "$CURRENT_OS_INSTALL_MOUNT" > "$TEMPFILE"` # to get arround bash variable scope difficulties
			fi
	
		else
			# this is probably a supporting disk, so we have to mount it browseable
			# TODO: add this mount to the list of things we are going to unmount
			# TODO: use union mounting to see if we can't co-mount this
			log "	Mounting a support disk from $INSTALLER_FOLDER/$IMAGE_FILE" 
			/usr/bin/hdiutil mount "$IMAGE_FILE" -readonly  >&4
		fi
	done
	
	CURRENT_OS_INSTALL_MOUNT=`/bin/cat "$TEMPFILE"` # to get arround bash variable scope difficulties
	/bin/rm "$TEMPFILE"
	
	if [ ! -d "$CURRENT_OS_INSTALL_MOUNT/System/Installation/Packages" ]; then
		log "ERROR: the main install disk was not sucessfully mounted!" 
		exit 1
	fi
	
	log "Mac OS X installer image mounted" 
	log 
	printf "\n" 
	printf "\n" 
}

# Install from installation media to the DMG
# The you can adjust the default language with the ISO_CODE variable.
#
# If you are running on 10.5 then InstaDMG will check for an InstallerChoices.xml file.
# This file will let you take control over what gets installed from the OSInstall.mpkg.
# Just place the file in the same directory as the instadmg script.

install_system() {
	log "#####Beginning Installation from $CURRENT_OS_INSTALL_MOUNT#####" 
	log "#####Beginning Installation from $CURRENT_OS_INSTALL_MOUNT#####" >&4
	log 
	log >&4
	printf "\n" 
	printf "\n" >&4
	if [ $OS_REV -eq 0 ]; then
		log "I'm running on Tiger. Not checking for InstallerChoices.xml file" 
		printf "\n" 
		/usr/sbin/installer -verbose -pkg "$CURRENT_OS_INSTALL_MOUNT/System/Installation/Packages/OSInstall.mpkg" -target $CURRENT_IMAGE_MOUNT -lang $ISO_CODE 
	else 
		log "I'm running on Leopard. Checking for InstallerChoices.xml file" 
			if [ -e ./BaseOS/InstallerChoices.xml ]
				then
				log "InstallerChoices.xml file found. Applying Choices" 
				printf "\n" 
				/usr/sbin/installer -verbose -applyChoiceChangesXML ./BaseOS/InstallerChoices.xml -pkg "$CURRENT_OS_INSTALL_MOUNT/System/Installation/Packages/OSInstall.mpkg" -target $CURRENT_IMAGE_MOUNT -lang $ISO_CODE 
				else
				log "No InstallerChoices.xml file found. Installing full mpkg" 
				printf "\n" 
				/usr/sbin/installer -verbose -pkg "$CURRENT_OS_INSTALL_MOUNT/System/Installation/Packages/OSInstall.mpkg" -target $CURRENT_IMAGE_MOUNT -lang $ISO_CODE 
			fi
		fi
		printf "\n" 
		printf "\n" >&4
		log "Base OS installed" 
		log "Base OS installed" >&4
		log 
		log >&4
		printf "\n" 
		printf "\n" 
		printf "\n" >&4
		printf "\n" >&4
}

# install packages from a folder of folders (01, 02, 03...etc)
install_packages_from_folder() {
	SELECTED_FOLDER="$1"
	
	log "+#####Beginning Update Installs from $SELECTED_FOLDER#####\n%H:%M:%S\n"
	log "+#####Beginning Update Installs from $SELECTED_FOLDER#####\n%H:%M:%S\n" >&4
	

	if [ "$SELECTED_FOLDER" == "" ]; then
		log "Error: install_packages_from_folder called without folder"
		exit 1;
	fi
	
	/bin/ls -A1 "$SELECTED_FOLDER" | /usr/bin/awk "/^[[:digit:]]+$/" | while read ORDERED_FOLDER
	do
		/bin/ls -A1 "$SELECTED_FOLDER/$ORDERED_FOLDER" | /usr/bin/awk 'tolower($1) ~ /\.(m)?pkg$/ && $1 !~ /^\._/' | while read UPDATE_PKG
		do
			if [ -e "$SELECTED_FOLDER/$ORDERED_FOLDER/InstallerChoices.xml" ]; then
				CHOICES_FILE="InstallerChoices.xml"
				# TODO: better handle multiple pkg's and InstallerChoice files named for the file they should handle
			fi
			
			if [ "$OS_REV" -eq 0 ]; then
				CHOICES_FILE="" # 10.4 can not use them
			fi			
			
			if [ "$CHOICES_FILE" != "" ]; then
				/usr/sbin/installer -verbose -applyChoiceChangesXML "$SELECTED_FOLDER/$ORDERED_FOLDER/$CHOICES_FILE" -pkg "$SELECTED_FOLDER/$ORDERED_FOLDER/$UPDATE_PKG" -target "$CURRENT_IMAGE_MOUNT"
				log "	Installed $SELECTED_FOLDER/$ORDERED_FOLDER/$UPDATE_PKG with XML Choices file: $CHOICES_FILE"
				log "	Installed $SELECTED_FOLDER/$ORDERED_FOLDER/$UPDATE_PKG with XML Choices file: $CHOICES_FILE" >&4
				
			else
				/usr/sbin/installer -verbose -pkg "$SELECTED_FOLDER/$ORDERED_FOLDER/$UPDATE_PKG" -target "$CURRENT_IMAGE_MOUNT"
				log "	Installed $SELECTED_FOLDER/$ORDERED_FOLDER/$UPDATE_PKG"
				log "	Installed $SELECTED_FOLDER/$ORDERED_FOLDER/$UPDATE_PKG" >&4
			fi
		done
	done
}

# clean up some generic installer mistakes
clean_up_image() {
	log "+$CREATE_DATE %H:%M:%S: Correcting some generic installer errors"
	log "+$CREATE_DATE %H:%M:%S: Correcting some generic installer errors" >&4
	
	# find all the symlinks that are pointing to $CURRENT_IMAGE_MOUNT, and make them point at the "root"
	/usr/bin/find -x "$CURRENT_IMAGE_MOUNT" -type l | while read THIS_LINK
	do
		if [ `/usr/bin/readlink "$THIS_LINK" | /usr/bin/grep -c "$CURRENT_IMAGE_MOUNT"` -gt 0 ]; then
		
			log "	Correcting soft-link: $THIS_LINK"
			CORRECTED_LINK=`/usr/bin/readlink "$THIS_LINK" | /usr/bin/awk "sub(\"$CURRENT_IMAGE_MOUNT\", \"\") { print }"`
			
			/bin/rm "$THIS_LINK"
			/bin/ln -fs "$CORRECTED_LINK" "$THIS_LINK"
		
		fi
	done
	
	# make sure that we have not left any open files behind
	/usr/sbin/lsof | /usr/bin/grep "$CURRENT_IMAGE_MOUNT/" | /usr/bin/awk '{ print $2 }' | /usr/bin/sort -u | /usr/bin/xargs /bin/kill 2>&1
}

# close up the DMG, compress and scan for restore
close_up_and_compress() {
	log "#####Creating the deployment DMG and scanning for ASR#####" 
	log 
	printf "\n" 
	
	# We'll rename the newly installed system to make it easier to work with later
	log "Rename the deployment volume" 
	#/usr/sbin/diskutil "rename $CURRENT_IMAGE_MOUNT $ASR_FS_NAME" 
	#CURRENT_IMAGE_MOUNT=/Volumes/$ASR_FS_NAME

	/usr/sbin/diskutil rename $CURRENT_IMAGE_MOUNT OS-Build-${CREATE_DATE} 
	CURRENT_IMAGE_MOUNT=/Volumes/OS-Build-${CREATE_DATE}
	log "New ASR source volume name is " $CURRENT_IMAGE_MOUNT 
	printf "\n" 

	# Create a new, compessed, image from the intermediary one and scan for ASR.
	log "Build a new image from folder..." 
	log 
	/usr/bin/hdiutil create -format UDZO -imagekey zlib-level=6 -srcfolder $CURRENT_IMAGE_MOUNT  ${ASR_FOLDER}/${CREATE_DATE} 
	log "New image created..." 
	log 
	printf "\n" 
	log "Scanning image for ASR" 
	log "Image to scan is ${ASR_FOLDER}/${CREATE_DATE}.dmg" 
	/usr/sbin/asr imagescan --verbose --source ${ASR_FOLDER}/${CREATE_DATE}.dmg 2>&1 
	
	printf "\n" 
	log 
	log "ASR image scan complete" 
	printf "\n" 
	printf "\n" 
}

# restore DMG to test partition
restore_image() {
	log "#####Restoring ASR image to test partition#####" 
	log 
	/usr/sbin/asr "--verbose --source ${ASR_FOLDER}/${CREATE_DATE}.dmg --target $ASR_TARGET_VOLUME --erase --nocheck --noprompt" 
	log "ASR image restored..." 
	log 
	printf "\n" 
	printf "\n" 
}

# set test partition to be the boot partition
set_boot_test() {
	log "#####Blessing test partition#####" 
	log 
	/usr/sbin/bless "--mount $CURRENT_IMAGE_MOUNT --setBoot" 
	log "Test partition blessed" 
	printf "\n" 
	printf "\n" 
}

# clean up
clean_up() {
	log "#####Cleaning up#####" 
	log 
	log "Ejecting images" 
	/usr/sbin/diskutil eject $CURRENT_IMAGE_MOUNT_DEV 
	/usr/sbin/diskutil eject $CURRENT_OS_INSTALL_MOUNT 
	log "Removing scratch DMG" 
	printf "\n" 
	/bin/rm ./DMG_Scratch/* 2>&1 
	printf "\n" 
	
}

# reboot the Mac
reboot() {
	log "#####Restarting#####" 
	log 
	/sbin/shutdown -r +1
}

# Timestamp the end of the build train.
timestamp() {
	log $CREATE_DATE 
	log 
	log $CREATE_DATE >&4
	log >&4
	log "InstaDMG Complete" 
	log "#############################################################" 
	log "InstaDMG Complete" >&4
	log "#############################################################" >&4
}

# Call the handlers as needed to make it all happen.

if [ $EUID != 0 ]
then
	rootcheck
fi

lang=""
SERVER_INSTALL="0"
exec 4>/dev/null
while getopts "l:svb:u:c:a:l:qh" opt
do
	echo "$opt" $OPTIND $OPTARG
	case $opt in
	l )
		lang="$OPTARG"
		;;
	b )
		INSTALLER_FOLDER="$OPTARG $INSTALLER_FOLDER"
		;;
	u )
		UPDATE_FOLDER="$OPTARG $UPDATE_FOLDER"
		;;
	c )
		CUSTOM_FOLDER="$OPTARG $CUSTOM_FOLDER"
		;;
	a )
		ASR_FOLDER="$OPTARG $ASR_FOLDER"
		;;
	d )
		DMG_SCRATCH="$OPTARG $DMG_SCRATCH"
		;;
	l )
		LOG_FOLDER="$OPTARG $LOG_FOLDER"
		;;
	s )
		SERVER_INSTALL="1"
		;;
	v )
		version
		exit 0
		;;
	q )
		exec 6>&1
		exec >>$LOG_FILE
		exec 4>>$PKG_LOG
		;;
	h )
		usage 
		exit 0
		;;
	"?" )
		printf "\n$0: invalid option -$OPTARG\n\n" >&2
		;;
	esac
done

shift $((OPTIND -1 ))

if [ "${lang%"${lang#?}"}" = "-" ] || [ "$lang" = "" ]
then
	printf "\n\tA language was not specified!!\n\n"
	bail
fi

#check_root
create_and_mount_image
mount_os_install
install_system
install_packages_from_folder "$UPDATE_FOLDER"
install_packages_from_folder "$CUSTOM_FOLDER"
clean_up_image
close_up_and_compress
clean_up
timestamp

# Automated restore options. Be careful as these can destroy data.
# restore_image
# set_boot_test
# reboot

exit 0
#!/bin/sh
export LANG=en_US.UTF-8
SERVER=$1
USERNAME=$2
PASSWORD=$3
ADDONROOT=$4
LOGROOT=$5
#service odoo stop
if [ "$6"x = "-r"x ] && [ ! -d "$DEST" ]
then
	REV=-r\ $7
	DEST=$ADDONROOT/$8
	/usr/bin/svn checkout $REV $SERVER/$8/trunk/$8 $DEST --no-auth-cache --non-interactive --username $USERNAME --password $PASSWORD | awk -F: 'BEGIN {print ""} {if(NR==1) print $0} END {print}' | /usr/bin/tee -a $LOGROOT/$8.log
	chown -R odoo $DEST
elif [ "$6"x = "-r"x ] && [ -d "$DEST" ]
then
	REV=-r\ $7
	DEST=$ADDONROOT/$8
	/usr/bin/svn update $REV $DEST --no-auth-cache --non-interactive --username $USERNAME --password $PASSWORD | awk -F: 'BEGIN {print ""} {if(NR==1) print $0} END {print}' | /usr/bin/tee -a $LOGROOT/$8.log
	find $DEST -name *.pyc -delete
	/bin/date >> $LOGROOT/$8.log
	chown -R odoo $DEST
elif [ "$6"x != "-r"x ] && [ ! -d "$DEST" ]
then
	ADDON=$6
	DEST=$ADDONROOT/$ADDON
	/usr/bin/svn checkout $SERVER/$ADDON/trunk/$ADDON $DEST --no-auth-cache --non-interactive --username $USERNAME --password $PASSWORD | awk -F: 'BEGIN {print ""} {if(NR==1) print $0} END {print}' | /usr/bin/tee -a $LOGROOT/$ADDON.log
	chown -R odoo $DEST
elif [ "$6"x != "-r"x ] && [ -d "$DEST" ]
then
	ADDON=$6
	DEST=$ADDONROOT/$ADDON
	/usr/bin/svn update $DEST --no-auth-cache --non-interactive --username $USERNAME --password $PASSWORD | awk -F: 'BEGIN {print ""} {if(NR==1) print $0} END {print}' | /usr/bin/tee -a $LOGROOT/$ADDON.log
	find $DEST -name *.pyc -delete
	/bin/date >> $LOGROOT/$ADDON.log
	chown -R odoo $DEST
fi
#service odoo start

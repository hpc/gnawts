#!/bin/bash
export lst="/var/log/opensm-subnet.lst"
export dump="/var/log/opensm-lfts.dump"
export dir="/tmp/routes/dumps"
# dump changes first, so monitor lst to make sure the snapshots correspond
while [ 1 ] ; do			# indefinitely monitor for new lst
    while ./inotifywait -q -q -e close_write $lst; do
	export now=`date +%s`
	cp -p $lst  $dir/$now.lst
	cp -p $dump $dir/$now.dump
	gzip $dir/$now.{dump,lst} &
    done
done

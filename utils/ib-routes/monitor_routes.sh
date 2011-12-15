#!/bin/bash
# run this on the subnet manager host, eg admin2-man on redsky
export routes="opensm-lfts.dump"
export splunkdir="/admin/splunk/infiniband"
while [ 1 ] ; do			# indefinitely monitor for new routes
    while ./inotifywait -q -q -e close_write /var/log/$routes; do
	date
	# run in a /tmp dir to avoid nfs delays
	cp -p /var/log/$routes ./	# avoid in-flight changes
	./routes.pl > routes.now	# walk all routes
	./routemerge.pl			# calculate changes since last time
	# splunkd.log says there are too many events at the same time, so it
	# adds around 7 sec around every 100K lines.  this introduces some time
	# imprecision despite the below careful timestamping.  the above takes 
	# about 100s to complete, and routes.diff ranges beteen .5 and 4.5M lines.
	# i'll take the "significant" cpu load reduction and set
	# DATETIME_CONFIG = NONE
	# since the strategy to minimal time imprecision is unclear.
	touch -r $routes routes.diff		    # set correct timestamp
	cp -p routes.diff $splunkdir/routes.diff    # copy to splunk dir (slow nfs)
	mv $splunkdir/routes.diff $splunkdir/routes # show changes to splunk
	mv routes.allnow routes.all	# prep for next time
	rm $routes			
    done
done

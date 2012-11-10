#!/usr/bin/perl
# MOAB stats RSV events do not use LLNL genders compressed host format
# as of 3/21/2012.  As a result, such lines can get extremely long and
# become truncated in transmission or import to Splunk, resulting in
# incorrect or incomplete component operations status (COS)
# information in Splunk-HPC's summary index.  To correct for this (or
# other manual corrections), have Splunk-HPC monitor a manually
# curated file.  Be careful, but this script can help...
# 
# This script can convert long RSV host lists into compressed LLNL
# genders format.  It can be run like `grep RSV moab/stats/events.* |
# CompressRSV.pl >> CompressedRSV.moabstats`.  If the raw moabstats
# logs are truncated, try forming your hostlist like this in
# Splunk-HPC:
#   index=summary orig_index=hpc_redsky | dedup orig_host | fields + orig_host | mvcombine orig_host | eval long=mvjoin(orig_host,",") | lookup hostlist long OUTPUT short | fields + short
# where redsky is the system name in this example (change that to your
# system name).  Once you have your hostlist, manually edit your
# event, and then append it to CompressedRSV.log.  Have Splunk-HPC
# monitor CompressedRSV.moabstats (add new lines to it as needed), the
# monitor stanza should declare it as sourcetype=moabstats.
#
# On redsky, truncation occurs at transmission via syslog-ng,
# so you have to get the raw events from admin3-man...

require Hostlist; # this comes from the llnlgenders Perl module

while (<>) { # for each line of stdin 
    next unless /\srsv\s/; # only work on RSV events
    if (/^\d\d:\d\d:\d\d+\s(\d+)/) { # lines do not start with a date
	@time = localtime $1;
	$time[4]+=1; # dumb months start at 0
	$time[5]+=1900; # dumb year starts at 1900
	$date = "$time[5]-$time[4]-$time[3]";
	$_ = "$date $_"; # prepend the date
    }
    if (/ALLOCNODELIST/) { # new explicit format
	($hosts) = /ALLOCNODELIST=(\S+)/;
	@hosts = split /,/, $hosts;
	$hostlist = Hostlist::compress(@hosts);
	$_ =~ s/ALLOCNODELIST=\S+/ALLOCNODELIST=$hostlist/;
	print;
    }
    else { # old implicit format
	@F = split;
	@hosts = split /,/, $F[13];
	$hostlist = Hostlist::compress(@hosts);
	$F[13] = $hostlist;
	print join " ", @F, "\n";
    }
}

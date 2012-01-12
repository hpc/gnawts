#!/usr/bin/perl
# This script backfills the summary index with host Component Operations Status (COS) state changes

$splunkFlags = "-preview false -header false -app hpc-jon";
$maxEventsSplunkGivesToCustomCommand = 50000;

$now = time;

sub latestSummary {
	return `splunk search "index=summary StateName | head 1 | stats max(_time)" $splunkFlags`;
}
sub latestCOSevent {
	return `splunk search "eventtype=cos_* | head 1 | stats max(_time)" $splunkFlags`;
}
sub utimeToSplunkFormat {
	$utime = shift;
	($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime($utime);
	$mon += 1; $year += 1900; # adjust for localtime offsets
	$splunkFormat = "$mon/$mday/$year:$hour:$min:$sec";
	return $splunkFormat;
}

# sanity check
$latestCOSevent = &latestCOSevent();
unless ($latestCOSevent) {
	die "ERROR: Nothing to do - there are no eventtype=cos_* events?!\n";
}

if ($#ARGV == 0) { # user indicate a number of days to backfill
	$daysago = shift @ARGV;
	$latestSummary = $now - $daysago*24*60*60;
}
else {  # otherwise, backfill since last summary, or 30 days if no summaries are found
	$latestSummary = &latestSummary();
	$latestSummary=~/\S/ or $latestSummary = $now - 30*24*60*60;
}
$ltime = localtime $latestSummary;
print STDERR "Preparing to backfill host state changes since $ltime...\n";

## create an array of @Latest times, which we can use to bound searches, so
## searches are faster due to time bounds (especially since we use tail)
$earliest=utimeToSplunkFormat($latestSummary+1);
$days = int(1 + ($now-$latestSummary)/(24*60*60)); # make sure splunk doesn't truncate at only 100 days (cli default maxout)
# get a map of how many events are on each day
@candidateEventsPerDay = `splunk search "earliest=$earliest eventtype=cos_* | timechart span=1d count" $splunkFlags -maxout $days`;
$eventsCount = 0;
foreach (@candidateEventsPerDay) {
	($yr,$mo,$day, $junk, $count) = /(\d+)-(\d+)-(\d+)\s+(\S+\s+\S+)\s+(\d+)/;
	if ($eventsCount + $count > 50000) {
		push @Latest, "$mo/$day/$yr:0:0:0";
		push @Counts, $eventsCount;
		while ($count>$maxEventsSplunkGivesToCustomCommand) {
			# very busy days will require multiple runs
			push @Latest, "$mo/$day/$yr:0:0:0";
			push @Counts, $maxEventsSplunkGivesToCustomCommand;
			$count -= $maxEventsSplunkGivesToCustomCommand;
		}
		$eventsCount = $count;
	}
	else {
		$eventsCount += $count;
	}
}
push @Latest, utimeToSplunkFormat($now);
push @Counts, $eventsCount;

## now actually do the backfill
$iters = scalar @Latest;
print STDERR "Backfilling will require $iters searches:";
$i=1;
while ($latest = shift @Latest) {
	$count = shift @Counts;
	print STDERR "\n==== ($i of $iters, $count events) ====> backfilling through $latest...\n";
	$search = '[search index=summary StateName | head 1 | eval query="(index=summary _time="._time." StateName) OR (_time>"._time." latest='.$latest.' eventtype=cos_*)" | fields + query] | tail 50000 | statechange | collect index=summary | stats count'; 
	if ($i++ == 1) { # first one may be special, see ARGV handling blocks
		$lastSummary = &latestSummary();
		unless ($lastSummary=~/\S/) {
			$search = "_time>$latestSummary latest=$latest eventtype=cos_* | tail 50000 | statechange | collect index=summary | stats count"; 
		}
	}
	$eventsCount =  `splunk search '$search' $splunkFlags`;
	chomp $eventsCount;
	print STDERR "$eventsCount host state changes were backfilled.\n";
	print STDERR "Waiting for summary index to be read.";
	sleep 5;
	$newSummary = &latestSummary;
	$loopCount = 1;
	while ($newSummary == $latestSummary) {
		print STDERR ".";
		sleep 5;
		$newSummary = &latestSummary;
		if ($loopCount++ >= 718) {
			die "\nERROR: giving up after an hour of waiting!\n";
		}
	}
	$latestSummary = &latestSummary();
	# print "\n"; print `splunk search "index=summary StateName | head 1" $splunkFlags`;
}

print STDERR "\nDONE!\n";

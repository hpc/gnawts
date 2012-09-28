#!/usr/bin/perl
# This script backfills the summary index with host Component Operations Status (COS) state changes

$splunkFlags = "-preview false -header false -app hpc";
$maxEventsSplunkGivesToCustomCommand = 50000;

$now = time;

sub latestSummary {
	$foo = `splunk search "index=summary StateName | head 1 | stats max(_time)" $splunkFlags`;
	chomp $foo;
	return $foo;
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

while ($arg = shift @ARGV) {
	if ($arg=~/\d+/) {
		$daysago = $arg;
		$latestSummary = $now - $daysago*24*60*60;
	}
	elsif ($arg=="-l") {
		$latestfile = shift @ARGV;
	}
}
unless ($daysago or $latestfile) {
	$latestSummary = &latestSummary();
	$latestSummary=~/\S/ or $latestSummary = $now - 30*24*60*60;
}

if ($latestfile) {
	# just redo a previous backfill (don't have to calculate how many runs are needed)
	open LATEST, $latestfile or die "can't open $latestfile for reading";
	$latestSummary = <LATEST>;
	chomp $latestSummary;
	while (<LATEST>) {
		($date, $count) = split;
		push @Latest, $date;
		push @Counts, $count;
	}
	close LATEST;
}
else {
$ltime = localtime $latestSummary;
print STDERR "Determining number of iterations needed to backfill since $ltime...\n";

## create an array of @Latest times, which we can use to bound searches, so
## searches are faster due to time bounds (especially since we use tail)
$earliest=utimeToSplunkFormat($latestSummary+1);
$days = int(1 + ($now-$latestSummary)/(24*60*60)); # make sure splunk doesn't truncate at only 100 days (cli default maxout)
# get a map of how many events are on each day
@candidateEventsPerDay = `splunk search "earliest=$earliest eventtype=cos_* | timechart span=1d count" $splunkFlags -maxout $days`;
$eventsCount = 0;
$bigDayCount = 0;
foreach (@candidateEventsPerDay) {
	($yr,$mo,$day, $junk, $count) = /(\d+)-(\d+)-(\d+)\s+(\S+\s+\S+)\s+(\d+)/;
	if ($bigDayCount) { # need multiple iterations for this day
		while ($bigDayCount>$maxEventsSplunkGivesToCustomCommand) {
			# very busy days will require multiple runs
			push @Latest, "$mo/$day/$yr:0:0:0";
			push @Counts, $maxEventsSplunkGivesToCustomCommand;
			$bigDayCount -= $maxEventsSplunkGivesToCustomCommand;
		}
		$eventsCount = $bigDayCount;
		$bigDayCount = 0;
	}
	if ($eventsCount + $count > 50000) {
		push @Latest, "$mo/$day/$yr:0:0:0";
		push @Counts, $eventsCount;
		$bigDayCount = $count;
	}
	else {
		$eventsCount += $count;
	}
}
push @Latest, utimeToSplunkFormat($now);
push @Counts, $eventsCount;

# save in case we want to rerun later via -l $latestfile
$latestfile = "/tmp/Latest.$$";
open LATEST, ">$latestfile" or die "can't open $latestfile";
print LATEST "$latestSummary\n";
$i=0;
foreach (@Latest) {
	print LATEST "$Latest[$i] $Counts[$i]\n";
	$i++;
}
close LATEST;
}

## actually do the backfill
$iters = scalar @Latest;
print STDERR "Backfilling will require $iters searches:";
$i=1;
while ($latest = shift @Latest) {
	$count = shift @Counts;
        $earliest = &utimeToSplunkFormat($latestSummary);
	$now = scalar localtime;
	print STDERR "\n===== $now: Working on $i of $iters ($count events) =====\n";
	$search = "earliest=$earliest latest=$latest (index=summary _time=$latestSummary StateName) OR (index=hpc_* _time>$latestSummary eventtype=cos_*) | tail 50000 | statechange | collect index=summary | stats count"; 
	if ($i==1) { # first one may be special, see ARGV handling blocks
		$lastSummary = &latestSummary();
		unless ($lastSummary=~/\S/) {
			$search = "_time>$latestSummary latest=$latest eventtype=cos_* | tail 50000 | statechange | collect index=summary | stats count"; 
		}
	}
    	print STDERR "Running: $search\n";
	$eventsCount =  `splunk search '$search' $splunkFlags`;
	chomp $eventsCount;
	if ($eventsCount > 0) {
	    print STDERR "Waiting for Splunk to read $eventsCount host state changes.";
	    sleep 5;
	    $newSummary = &latestSummary();
	    $loopCount = 1;
	    while (!$newSummary or $newSummary == $latestSummary) {
		print STDERR ".";
		sleep 5;
		$newSummary = &latestSummary();
		if ($loopCount++ >= 718) {
			die "\nERROR: giving up after an hour of waiting!\n";
		}
	    }
	}
	else {
	    print STDERR "WARNING: This should never happen: $eventsCount host state changes.";
	}
	$latestSummary = $newSummary;
	$i++;
	# print "\n"; print `splunk search "index=summary StateName | head 1" $splunkFlags`;
}

print STDERR "\nDONE!\n";

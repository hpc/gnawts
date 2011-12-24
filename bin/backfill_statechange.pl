#!/usr/bin/perl
# This script backfills the summary index with host Component Operations Status (COS) state changes

$now = time;

sub latestSummary {
	return `splunk search "index=summary StateName | head 1 | stats max(_time)" -preview false -header false`;
}
sub latestCOSevent {
	return `splunk search "eventtype=cos_* | head 1 | stats max(_time)" -preview false -header false`;
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
	$latestSummary = &latestSummary() or $now - 30*24*60*60;
}


while ($latestCOSevent > $latestSummary and $latestCOSevent < $now) {  
	# keep the user informed...
	$ltime = localtime $latestSummary;
	warn "Backfilling since $ltime\n";

	# do it
	`splunk search \"_time>$latestSummary eventtype=cos_* | tail 50000 | statechange | collect index=summary\"` or 
		die "Update failed: $!\n";

	$latestSummary = &latestSummary();
	$latestCOSevent = &latestCOSevent();
}
warn "DONE!\n";


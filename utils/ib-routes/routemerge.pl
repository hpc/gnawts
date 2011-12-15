#!/usr/bin/perl

# given two route files from route.pl (a and b),
# 1. write all known (latest) routes into AllNow
# 2. write differences (new or changed) to Diff

$Previous = "routes.all";
$Now  = "routes.now";
$AllNow = "routes.allnow";
$Diff = "routes.diff";
$Ldiff = "routes.csv";

@s = stat "opensm-lfts.dump";
$time = @s[10];

open PREV, $Previous or die "can't open $Previous: $!\n";
open NOW, $Now or die "can't open $Now: $!\n";
open ALLNOW, ">$AllNow" or die "can't open $AllNow: $!\n";
open DIFF, ">$Diff" or die "can't open $Diff: $!\n";
open LDIFF, ">>$Ldiff" or die "can't open $Ldiff: $!\n";

NEXTOLD:
while ($old or $old=<PREV>) {
	while ($new or $new=<NOW>) {
		if ($old eq $new) {	# lines match
			print ALLNOW $old;	# write to all.routes
			$old = $new = ''; # done with old and new lines
			goto NEXTOLD; 	# next old line
		}
		else { # lines do not match
			@old = split /\s+/, $old;
			@new = split /\s+/, $new;
			$srccmp = $old[0] cmp $new[0]; # compare src
			if ($srccmp<0) { 	# old line doesn't exist in new
				print ALLNOW $old;	# write to all.routes
				$old = ''; 		# done with old line
				goto NEXTOLD; 	# next old line
			}
			elsif ($srccmp>0) {	# new line doesn't exist in old
				print ALLNOW $new;
				print DIFF $new;
				$new = '';		# done with new line
				next;			# next new line
			}					
			else { # src's match
				$dstcmp = $old[-1] cmp $new[-1];
				if ($dstcmp<0) { 	# old line doesn't exist in new
					print ALLNOW $old;	# write to all.routes
					$old = ''; 		# done with old line
					goto NEXTOLD; 	# next old line
				}
				elsif ($dstcmp>0) {	# new line doesn't exist in old
					print ALLNOW $new;
					print DIFF $new;
					save_lookup($new);
					$new = '';		# done with new line
					next;			# next new line
				}					
				else {	# src and dest match, new supercedes old
					print ALLNOW $new;
					print DIFF $new;
					save_lookup($new);
					$old = $new = ''; # done with old and new lines
					goto NEXTOLD; 	# next old line
				}
			}
		}
	}
	# only way to get here is if NOW is at EOF
	while ($old=<PREV>) { # save remaining old lines
		print ALLNOW $old; 
	}
	last;
}
if ($new) { 
	while ($new or $new=<NOW>) { # save remaining new lines
		print ALLNOW $new;	
		print DIFF $new;
		save_lookup($new);
		$new = '';		# done with new line
	}
}

close LDIFF;
close DIFF;
close ALLNOW;
close NOW;
close PREV;

sub save_lookup() {
	$line = shift;
	@route = split /\s+/, $line;
	$src = shift @route;
	$dest = pop @route;
	$route = join " ", @route;
	print LDIFF join ",", $time,$src,$route,$dest;
	print LDIFF "\n";
}

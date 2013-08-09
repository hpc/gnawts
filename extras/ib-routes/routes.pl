#!/usr/bin/perl

# make this a CLI arg instead
&setup_lookups();

&read_routes();
&read_topology();
&print_routes_for_all_host_permutations();
#&print_cables_lookup(); # uncomment to generate links.csv

exit;

#########################################################################
sub setup_lookups() {
  # node to guid
  $mapfile = &findfile("/admin/etc/GUID.yml");
  open MAP, $mapfile or die "can't open $mapfile: !$\n";
  while (<MAP>) {
	next if /^#/; # eat comments
	($name, $guid) = /^(\S+):\s+0x(\S+)/;
	$name{$guid} = $name;
  }
  close MAP;

  # switch to guid 
  $mapfile = &findfile("/admin/etc/ib-node-name-map.master");
  open MAP, $mapfile or die "can't open $mapfile: !$\n";
  while (<MAP>) {
	next if /^#/; # eat comments
	($guid, $name) = /^0x(\S+)\s+"(\S+)"/;
	$name{$guid} = $name;
  }
  close MAP;
}

sub read_routes() { # port is in decimal
  $routesfile = &findfile("/var/log/opensm-lfts.dump");
  open ROUTES, $routesfile or die "can't open $routesfile: !$\n";
  while (<ROUTES>) {
	next if /^#/; # eat comments
	if (/^Unicast lids/) { # a new switch
		($switch) = /'(\S+)'/;
	}
	else {
		if (%name) { # use guid lookups - even for switches
			($guid) = /portguid 0x(\S+):/;
			$dest = $name{$guid};
		}
		else { # depend on pool name being first word of ib description
			($dest) = / '(\S+)/;  #' fix vim syntax coloring
		}
		($port) = / ([0-9]+) /;
		$route{$switch}{$dest} = sprintf "%d", $port;
	}
  }
  close ROUTES;
}

sub read_topology() { # port is in hex
  $topologyfile = &findfile("/var/log/opensm-subnet.lst");
  open LINKS, $topologyfile or die "can't open $topologyfile: $!\n"; #' fix vim syntax coloring
  while (<LINKS>) {
	next unless /^\{ SW/; # skip host-first entries (redundant)
	# link has two ends: a and b.  a is always a switch due to the above
	if (%name) { # use guid lookups
		($aguid, $aport, $bguid, $bport) = /PortGUID:(\S+) .* PN:(\S+) .* PortGUID:(\S+) .* PN:(\S+)/;
		$aname = $name{$aguid};
		$bname = $name{$bguid};
	}
	else { # depend on pool name being first word of ib description
		($aname, $aport, $bname, $bport) = /\{(\S+)\} LID:\S+ PN:(\S+) .* \{(\S+).*\} LID:\S+ PN:(\S+)/;
	}
	if (/\{ CA/) {
		# when we add hostlist as CLI arg, expand into %hostlist and uncomment the below
		# next if (%hostlist and exists %hostlist{$bname}); # don't care or already have it
		push @hosts, $bname;
		$b = $bname;
	}
	else {
		$b = sprintf "%d:%s", hex($bport), $bname;
	}
	$a = sprintf "%d:%s", hex($aport), $aname;
	$link{$a} = $b; 
	$link{$b} = $a; # do both ends of the cable (relates to above "redundant" comments)
  }
  close LINKS;
  @hosts = sort @hosts; # enables efficient detection of route changes
}

sub print_routes_for_all_host_permutations() {
  foreach $from (@hosts) {
	foreach $to (@hosts) {
		next if ($from eq $to);
		# walk the route
		@hops = ($from, $link{$from});
		while ($hops[-1]=~/\S+:(\S+)$/) {
			$hop = $1;
			$outport = $route{$hop}{$to};
			$hops[-1] .= sprintf ":%d", $outport;
			$a = $outport . ":" . $hop;
			push @hops, $link{$a};
		}
		print join " ", @hops;
		print "\n";
	}
  }
}

sub findfile() {
	$file = shift;			# given a /full/path/to/filename
	@F = split /\//, $file;
	$f = $F[-1];
	$file = $f if (-s $f);	# return filename if there is a nonzero one in the cwd
	return $file;		# otherwise return /full/path/to/filename
}

sub print_cables_lookup() {
	# logic is hard-coded and solely based on siwtch name and port numbers,
	# so it is sufficient to run this once and save results as a splunk lookup table
	open LOOKUPS, '>links.csv' or die "cant open links.csv: $!\n";
	print LOOKUPS "host,port,direction,dest,link,dlink,connection\n"; # header defines columns
	foreach $a (sort keys %link) {

		($aname, $aport, $adirection, $alink) = &name_port_direction_link($a);
		($bname, $bport, $bdirection, $blink) = &name_port_direction_link($link{$a});

		# link name (one for each end of the link)
		$link  = join ' <--> ', $alink, $blink; 	   

		# dlink name (one for each link)
		$dlink = $link;
		if ($adirection eq 'host' or $adirection gt $bdirection) {
			$dlink  = join ' <--> ', $blink, $alink; 	   
		}

		$cable = $dlink;
		if ($cable=~/\) </) { # not a host cable
			$cable =~ s/ \(\d+\)//g; # so omit port info (one for each cable)
		}

		$adirection = 'switch' unless $adirection;
		print LOOKUPS "$aname,$aport,$adirection,$bname,\"$link\",\"$dlink\",\"$cable\"\n";
	}
}

sub name_port_direction_link($) {
	$porthost = shift;
	if ($porthost!~/:/) { # an HCA
		$name = $porthost;
		$port = 1;
		$direction = '';
		$link = $name;
	}
	else {
		($port, $name) = split /:/, $porthost;
		$direction = &direction($name, $port);
		if ($direction eq 'host') {
				$link = $name .' ('. $port .')';
		}
		else {
				$link = $name .','. $direction .' ('. $port .')';
		}
	}

	return ($name, $port, $direction, $link);
}

sub direction($$) {
	my $switch_phys_name = shift;
	my $switch_port      = shift;
	my $direction = '';

	if ($switch_phys_name!~/a|b/ or $switch_port<1 or $switch_port>36) {
		# return []; # name or port is outside our knowledge
	}
	elsif ($switch_port <= 3) {
		$direction = ($switch_phys_name =~ /a/) ? '-z' : '+z';
	}
	elsif ($switch_port <= 6) {
		$direction = '+y';
	}
	elsif ($switch_port <= 9) {
		$direction = '-y';
	}
	elsif ($switch_port <= 12) {
		$direction = '+x';
	}
	elsif ($switch_port <= 15) {
		$direction = '-x';
	}
	elsif ($switch_port <= 27) { # host ports
		$direction = 'host'; # or "in"
	}
	else {
		$direction = ($switch_phys_name =~ /b/) ? '-z' : '+z';
	}

	return $direction;
}

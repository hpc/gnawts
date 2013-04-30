#/usr/bin/sh
# given old.routes and new.routes as inputs, put timestamped diffs into old-new.diff.
# old and new must be a number, indicating the utime of the route dump

# extract the heads of the filenames
export a=$(basename $1 .routes)
export b=$(basename $2 .routes)
# output filename is concatenation of the inputs
export d=$a-$b.diff

# sanity check
export g=$((a-b))
if [[ $g > 0 ]]; then
	echo "WARNING: second filename should indicate a later time (but $a > $b)..."
fi

# do the diff
diff $1 $2 | grep '^>' | perl -ne "s/^(>)/$b/; print;" > $d

# update the timestamp of the output file for handy listing
touch -r $1 $d

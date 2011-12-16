#/usr/bin/sh
# given two input filenames, put the diffs into a third

# do the diff
diff $1 $2 | grep '^>' | perl -ne 'print substr $_,2' > $3
# update the timestamp
touch -r $1 $3

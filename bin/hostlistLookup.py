import csv,sys,os,hostlist,logging,re
#from hostlist import expand_hostlist, collect_hostlist, numerically_sorted, Bn s.split(",")]adHostlist, __version__ as library_version
# example usage in splunk search:
# nnodes=16 | head 1 | lookup hostListLookup hostlist | makemv delim="," new_hostlist | mvexpand new_hostlist
# nnodes=16 | head 1 | lookup hostListLookup short | makemv delim="," long | mvexpand long
# to excersize forward and backward:
# nnodes=16 | head 1 | lookup hostListLookup short | lookup hostListLookup long OUTPUTNEW short AS new_short

#LOG_FILENAME = '/tmp/output_from_splunk.txt'
LOG_FILENAME = '/tmp/hostlistLookup.log'
logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG)

def debug(msg):
  #logging.debug(msg)
  return

# this is the forward lookup to take a list like this [1-10,15-16,18] and return
# this: 1,2,3,4,5,6,7,8,9,10,15,16,18
def lookup(list):
  debug("Forward Lookup:")
  debug(list)
  if "*" in list or ":" in list:
    # MOAB events on Cray XE6 use node list format [1-7]*16:[10-99]*7
    list = re.sub("\*\d+","", list) # omit *nprocs
    list = re.sub(":",",", list)    # change : to ,
  new_list = hostlist.expand_hostlist(list)
  # this takes the list we get back and turns it into a string for splunk
  return ",".join(str(n) for n in new_list)

# this is the reverse lookup to take this: 1,2,3,4,5,6,7,8,9,10,15,16,18
# and return a list like this [1-10,15-16,18]
def rlookup(list):
  debug("Reverse Lookup:")
  debug(list)
  # hostlist does not like square brackets, so get rid of them
  # this turns a string obj into a list obj
  new_list = [str(n) for n in list.replace("[","").replace("]", "").split(",")]
  return hostlist.collect_hostlist(new_list)

def main():
  # we can have 2 args
  # we can tell which list comes in through splunk
  # and based on those lists we will do a reverse or forward lookup
  # python expand_hostlist.py long_list short_list
  # python expand_hostlist.py short_list long_list
  if len(sys.argv) < 3:
    debug("Usage: python expand_hostlist.py [short|long list] [long|short list]")
    print "Usage: python expand_hostlist.py [short|long list] [long|short list]"
    sys.exit(0)

  listf     = sys.argv[1]
  new_listf = sys.argv[2]
  debug(listf)
  debug(new_listf)

  # splunk passes in csv data and we take each row and do a lookup
  rows = csv.reader(sys.stdin)

  debug("got the rows")
  i = 0
  first = True
  header = []
  for line in rows:
    if first:
      header = line
      if listf not in header:
        print "List field must be in CSV data"
        sys.exit(0)
      csv.writer(sys.stdout).writerow(header)
      # we return csv data for splunk too
      w = csv.DictWriter(sys.stdout, header)
      first = False

    result = {}
    i = 0
    # get the header
    while i < len(header):
      if i < len(line):
        result[header[i]] = line[i]
      else:
        result[header[i]] = ''
      i += 1

    if len(result[listf]) and len(result[new_listf]):
      w.writerow(result)
    elif len(result[listf]):
      result[new_listf] = lookup(result[listf])
      w.writerow(result)
    elif len(result[new_listf]):
      # reverse it ... rlookup()
      result[listf] = rlookup(result[new_listf])
      w.writerow(result)

  debug("done with rows")

debug("Starting .....")
main()
debug("Finished")

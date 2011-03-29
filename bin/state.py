import csv,sys,os,hostlist,logging
# example usage in splunk search:
# nnodes=16 | head 1 | lookup hostListLookup hostlist | makemv delim="," new_hostlist | mvexpand new_hostlist
# nnodes=16 | head 1 | lookup hostListLookup short | makemv delim="," long | mvexpand long
# to excersize forward and backward:
# nnodes=16 | head 1 | lookup hostListLookup short | lookup hostListLookup long OUTPUTNEW short AS new_short
# tag=statechange NOT jobstart | sort _time | search node="c0-0c1s6n1" | lookup stateLookup node eventtype

LOG_FILENAME = '/tmp/output_from_splunk.txt'
logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG)

node_states = {}

def debug(msg):
  logging.debug(msg)
  return

def store_current_state(node, state):
  debug("Storing current state ######################################")
  debug("Node to store to hash: " + node)
  debug("State to store to hash: " + state)
  global node_states
  debug("Current hash: " + str(node_states))
  node_states[node] = state
  debug("Updated hash: " + str(node_states))

def get_current_state(node):
  debug("Getting current state ######################################")
  debug("Node to lookup: " + node)
  global node_states
  debug("Current hash: " + str(node_states))
  return node_states.get(node) 

# derive state for given node and eventtype
# node can come in as a single node or list of nodes 
# the list of nodes can be in short (1-3) or long (1,2,3) form
# each node can have a different state or NOT a state at all
# only return the nodes that have a new state applied
def get_state(node, eventtype): #, last_eventtype):
  debug("Getting state node and event type ##########################")
  debug("Node: " + node)
  debug("Eventtype: " + eventtype)
#  prev_state, current_state = last_eventtype.split("-")
  start_state, end_state = eventtype.split("-")
  debug("Start state from eventtype: " + start_state)
  debug("End state from eventtype: " + end_state)
  node_list = hostlist.expand_hostlist(node)
  new_node_list = []
  for single_node in node_list:
    current_state = get_current_state(single_node)
    debug("Current state from lookup: " + str(current_state))
    if current_state == start_state:
      new_node_list.append(single_node)
    store_current_state(single_node, end_state)

  # TODO what do I do with the non-appended nodes that did not actually change state?
#  return [hostlist.collect_hostlist(new_node_list), end_state]
  return [hostlist.collect_hostlist(node_list), end_state]

def main():
  # we must have 2 args
  # python state.py node eventtype last_eventtype
  if len(sys.argv) < 4:
    debug("Usage: python state.py node eventtype _time") 
    print "Usage: python state.py node eventtype _time"
    sys.exit(0)

  nodef      = sys.argv[1]
  eventtypef = sys.argv[2]
#  last_eventtypef = sys.argv[3]
#  debug(nodef)
#  debug(eventtypef)

  # splunk passes in csv data and we take each row and do a lookup
  rows = csv.reader(sys.stdin)

#  debug("got the rows")
  i = 0
  first = True
  header = []
  for line in rows:
    debug("LINE #######################################################")
    debug(line)
    if first:
      header = line
#      debug("Header: " + header)
      if nodef not in header or eventtypef not in header: # or last_eventtypef not in header:
        print "Node, EventType and Last EventType fields must be in CSV data"
        sys.exit(0)
      # add the state field to the CSV
      header.append("state")
      csv.writer(sys.stdout).writerow(header)
      # we return csv data for splunk too
      w = csv.DictWriter(sys.stdout, header)
      first = False
      continue

    result = {}
    i = 0
    while i < len(header):
      if i < len(line):
        result[header[i]] = line[i]
      else:
        result[header[i]] = ''
      i += 1

#    debug(result)
    # we will be updating the node list too
    result[nodef], result['state'] = get_state(result[nodef], result[eventtypef]) #, result[last_eventtypef])
    debug("Result: " + str(result))    
    if len(result[nodef]):
      debug("Writing csv out: " + str(result))
      w.writerow(result)

#  debug("done with rows")

debug("******************************************* Starting ...")
main()
debug("... Finished *******************************************")

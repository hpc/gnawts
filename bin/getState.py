import sys,os,splunk.Intersplunk,hostlist,logging,ast,pickle

# Example: tag=statechange NOT jobstart | search node="c0-0c1s6n1" | head 24 | getstate
# to return ALL resuls even those not changing state use filter option of False
# Example: tag=statechange | getstate {'filter':False} 
# this will return only those records with state change
# Example: tag=statechange | getstate
# if your node field is other than "node", i.e., "nodes" set the nodeField option (defaults to 'node')
# Example: tag=statechange | getstate {'nodeField':'nodes'}
# if you don't want to preload node states or write out node states then set useNodeStatesFile to false
# Example: tag=statechange | getstate {'useNodeStatesFile':False}
# if you need to use more than one option then put them in quotes
# tag=statechange | getstate "{'filter':False, 'useNodeStatesFile':False}" | table _time node eventtype state

LOG_FILENAME = '/tmp/output_from_splunk_2.txt'
logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG)

PICKLE_FILENAME = 'data.pkl'

options = {'filter': True, 'nodeField':'node', 'useNodeStatesFile': True}
results = []
output_results = []
node_states = {}

# easy way to log data to LOG_FILENAME
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
def update_states(record): #, last_eventtype):
  global output_results, options
  node = record.get(options.get('nodeField'))
  eventtype = record.get('eventtype')
  # if we don't have node or eventtype then skip
  if not eventtype or not node:
    return
  debug("Getting state node and event type ##########################")
  debug("Node: " + node)
  debug("Eventtype: " + eventtype)
  # eventtypes can come in as many eventtypes, i.e., "USR-ERR donna-ignore"
  # in all cases, we want the FIRST eventtype which is the statechange
  eventtypes = eventtype.split(" ")
  # now get our start and end states
  if not eventtypes:
    return
  start_state, end_state = eventtypes[0].split("-")
  if not start_state or not end_state:
    return
  debug("Start state from eventtype: " + start_state)
  debug("End state from eventtype: " + end_state)
  node_list = hostlist.expand_hostlist(node)
  new_node_list = []
  for single_node in node_list:
    current_state = get_current_state(single_node)
    debug("Current state from lookup: " + str(current_state))
    new_record = record
    new_record[options.get('nodeField')] = single_node
    if current_state == start_state:
      new_record['state'] = end_state
    if new_record.get('state') or not options.get('filter'):
      output_results.append(new_record)
    store_current_state(single_node, end_state)

def setup_node_states(pkl_file):
  try: 
    return pickle.load(pkl_file)
  except EOFError:
    return {}

def main():
  try:
    global results, options, node_states
    results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()

    debug(sys.argv)

    # flag to filter or not filter non-stated events
    # filter defaults to True
    if len(sys.argv) > 1:
      new_options = ast.literal_eval(sys.argv[1])
      options.update(new_options)

    debug("OPTIONS: " + str(options))

    if options.get('useNodeStatesFile'):
      # this is our pickle file ... used for serializing our state data
      # so we have previous states for nodes
      pkl_file = open(PICKLE_FILENAME, 'ab+')
      node_states = setup_node_states(pkl_file)
      pkl_file.close()

    # our node states
    debug("Node States: ")
    debug(node_states)

    # sort the results by time
    for r in sorted(results, key=lambda k: k['_time']):
      update_states(r)

    if options.get('useNodeStatesFile'):
      # dump the pickle data (our previous node states)
      pkl_file = open(PICKLE_FILENAME, 'wb')
      pickle.dump(node_states, pkl_file)
      pkl_file.close()
  except:
    import traceback
    stack =  traceback.format_exc()
    results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

  splunk.Intersplunk.outputResults( output_results )


debug("Starting")
main()
debug("Finished")

# Here is how this stateChange script fits into the RAS Metrics implementation:
# 1. Node state logic is encoded as eventtypes, formatted as FROM-TO where
#    FROM and TO are arbitrary state names.  For example, events matching
#    etype=nodedown could have eventtype=USR-ERR.  All such eventtypes must
#    have priority=1 (appear first in the eventtype field), and be grouped via
#    tag=state.
# 3. this script processes such events which include a node field (events without
#    a node field are ignored), and outputs:
#   a. one event per actual node state change, including:
#        _time node=NODE nodeStateChange=FROM-TO 
#   b. one event per system state change, including:
#        _time systemStateChange=FROM-TO 
#      this should only occur if an argument FROM-TO_Threshold is given,
#      for example USR-ERR_Threshold=10 would result in an event like
#        _time systemStateChange=USR-ERR
#      when the total number of nodes in an ERR state become >= 10, and 
#        _time systemStateChange=USR-ERR
#      when the running count of nodes in ERR becomes <10.  "Becomes" means
#      that events should only be output when the threshold is crossed
#      (eg, not all nodeStateChange events cause a threshold crossing).
#   c. just before exiting, an event including:
#        _time eventtype=nodeStateList XXX=hostlist YYY=hostlist ZZZ=hostlist
#      where _time is the time of the last seen event (regardless of whether it
#      resulting in a nodeStateChange), XXX, YYY, and ZZZ are state names and
#      hostlist is a compressed list of the nodes in each state.  For example:
#        _time eventtype=nodeStateList USR=[1-50,71-90] ERR=[51-60,91-92] SYS=[61-70,93-100]
#      indicates 70 nodes in USR, 12 nodes in ERR, and 17 in SYS.
#   NOTE - output events should be a copy of the triggering event, with the
#      above fields added in as appropriate.
# 4. the output events of this script are saved to a summary index, for example:
#        tag=state | stateChange | collect index=summary
#     would store state changes into the summary index, using no initial
#     state information, such that the earliest event for each node results in a
#     nodeStateChange.  In contrast, tracking of state across invocations of
#     this script is accomplished by using the latest nodeStateList in the
#     summary index, for example:
#        [search index=summary eventtype=nodeStateList | head 1 | eval query="(index=summary eventtype=nodeStateList) OR (tag=state earliest="._time.")" | fields + query] | stateChange | collect index=summary
#     will result in this script setting the initial state of nodes via the
#     nodeStateList event it receives as input (eg, the one from the last time
#     this script ran), and then it will process in the normal way the other
#     input events (eg, all the tag=state events events since the last time
#     this script ran).  This latter example will be periodically run as a
#     scheduled saved search.
#
# At this point, various per-node and system metrics are possible, for example:
# MTTI is the mean time a node (or system) stays in a  USR state, and 
# MTTR is the mean time a node (or system) stays in an ERR state.
# These will be accomplished via saved searches and macros which process
# nodeStateChange and systemStateChange events from the summary index.

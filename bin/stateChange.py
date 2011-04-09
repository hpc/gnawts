import sys,os,splunk.Intersplunk,hostlist,logging,ast,re

# Example: tag=state NOT jobstart | search node="c0-0c1s6n1" | head 24 | statechange
# to return ALL resuls even those not changing state use filter option of False
# Example: tag=state | statechange {'filter':False} 
# this will return only those records with state change
# Example: tag=state | statechange
# if your node field is other than "node", i.e., "nodes" set the nodeField option (defaults to 'node')
# Example: tag=state | statechange {'nodeField':'nodes'}
# if you don't want to preload node states or write out node states then set useNodeStatesFile to false
# Example: tag=state | statechange {'useNodeStatesFile':False}
# if you need to use more than one option then put them in quotes
# tag=state | statechange "{'filter':False, 'useNodeStatesFile':False}" | table _time node eventtype state

# tag=state NOT jobstart | statechange "{'ERR-USR_Threshold' : 5}" | table _time eventtype node nodeStateChange systemStateChange crossing

LOG_FILENAME = '/tmp/output_from_splunk_2.txt'
logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG)

options = {'filter': True, 'nodeField':'node', 'addAggregate': True}
trigger_options = {}
results = []
output_results = []
node_states = {}
node_transitions = {}

# easy way to log data to LOG_FILENAME
def debug(msg):
  logging.debug(msg)
  return

# store state transitions for counting later
def store_state_transition(node, transition):
  debug("Storing state transition")
  debug("Node to store to hash: " + node)
  debug("Transition to store to hash: " + transition)
  global node_transitions
  node_transitions[node] = transition

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
  
  update_output_results_for_node(record, node, start_state, end_state)

def update_output_results_for_node(record, node, start_state, end_state):
  global output_results, trigger_options
  node_list = hostlist.expand_hostlist(node)

  for single_node in node_list:
    previous_transition = node_transitions.get(node)
    current_state = get_current_state(single_node)
    debug("Current state from lookup: " + str(current_state))
    appended_new_record = False
    new_record = record
    new_record[options.get('nodeField')] = single_node
    new_transition = start_state + "-" + end_state
    reverse_transition = end_state + "-" + start_state
    if current_state == start_state or not current_state:
      new_record['nodeStateChange'] = new_transition
      new_record[end_state] = len(all_nodes_in_state(end_state)) + 1
      new_record[start_state] = len(all_nodes_in_state(start_state)) - 1
      if new_record.get(start_state,0) < 0:
        new_record[start_state] = 0
    if new_record.get('nodeStateChange') or not options.get('filter'):
      store_state_transition(node, new_record.get('nodeStateChange'))
      output_results.append(new_record)
      add_trigger_transition(new_record, previous_transition, new_transition, reverse_transition)
    store_current_state(single_node, end_state)

def add_trigger_transition(record, previous_transition, new_transition, reverse_transition): 
  debug("Adding Trigger Transition to event")
  global trigger_options, node_transitions, output_results
  # if we 
  # 1) added a new record and 
  # 2) have trigger thresholds for eventtypes and
  # 3) and our record's current or previous state transition matches one of the keys
  # then we can talk transition:
  if len(trigger_options) and ((new_transition and trigger_options.has_key(new_transition + "_Threshold")) or (previous_transition and trigger_options.has_key(previous_transition + "_Threshold"))):
    debug("We have what we need to add trigger")
    # get the aggregate dict for node transitions
    # basically from node => transition -to- transition => [nodem ... noden]
    aggregate_transitions = aggregate_dict(node_transitions)
    # count is increasing for new_transition and decreasing for previous transition
    # for new transition we only care about points of upward crossing, that's >= for going UP, so really just == VALUE for threshold
    if new_transition and trigger_options.has_key(new_transition + "_Threshold") and len(aggregate_transitions.get(new_transition,[])) == trigger_options.get(new_transition + "_Threshold"): 
      debug("UPWARD Trigger for " + new_transition + "_Threshold")
      trigger_record = {'_time': record.get('_time'), 'systemStateChange': new_transition, 'crossing': 'increasing'}
      output_results.append(trigger_record)

    # count is decreasing for previous_transition
    # for previous transitions we only care about points of downward crossing, that's < for going DOWN, so really just == VALUE for threshold minus 1
    if previous_transition and trigger_options.has_key(previous_transition + "_Threshold") and len(aggregate_transitions.get(previous_transition,[])) == trigger_options.get(previous_transition + "_Threshold") - 1: 
      debug("DOWNWARD Trigger for " + previous_transition + "_Threshold")
      trigger_record = {'_time': record.get('_time'), 'systemStateChange': previous_transition, 'crossing': 'decreasing'}
      output_results.append(trigger_record)

def setup_node_states():
  try: 
    #TODO return something
    return {}
  except EOFError:
    return {}

def all_nodes_in_state(state):
  global node_states
  nodes_by_state = aggregate_dict(node_states)
  return nodes_by_state.get(state, [])

# swap from node => state to state => [node0...noden]
# or any dict from node => transition to transition => [node ... noden]
def aggregate_dict(adict):
  new_hash = {}
  # now add to the aggregate event by looping through our node_states
  for k,v in adict.iteritems():
    new_v = new_hash.get(v, [])
    new_v.append(k)
    new_hash[v] = new_v

  return new_hash

def build_aggregate_event(r):
  global node_states, output_results
  debug("Building Aggregate Event")
  aggregate_event = {'_time': r['_time'], 'eventtype': 'nodeStateList'}
  new_hash = aggregate_dict(node_states)

  # put in proper form
  for k,v in new_hash.iteritems():
    new_hash[k] = hostlist.collect_hostlist(v)

  aggregate_event.update(new_hash)
  output_results.append(aggregate_event)
  

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
      for k in filter(lambda x: re.match(".*_Threshold$", x), options.keys()):
        trigger_options[k] = options[k]

    debug("OPTIONS: " + str(options))

    # TODO get from passed in data
    node_states = setup_node_states()

    # our node states
    debug("Node States: ")
    debug(node_states)

    # sort the results by time
    if len(results) and results[0].has_key('_time'):
      last_record = None
      for r in sorted(results, key=lambda k: k['_time']):
        update_states(r)
        last_record = r
      if options.get('addAggregate'):
        # need the last record for '_time' entry
        build_aggregate_event(last_record)

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
# 2. this script processes such events which include a node field (events without
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
#      resulted in a nodeStateChange), XXX, YYY, and ZZZ are state names and
#      hostlist is a compressed list of the nodes in each state.  For example:
#        _time eventtype=nodeStateList USR=[1-50,71-90] ERR=[51-60,91-92] SYS=[61-70,93-100]
#      indicates 71 nodes in USR, 12 nodes in ERR, and 18 in SYS.
#   NOTE - output events should be a copy of the triggering event, with the
#      above fields added in as appropriate.
# 3. the output events of this script are saved to a summary index, for example:
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


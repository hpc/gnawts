import sys,splunk.Intersplunk,hostlist,logging

# Example: tag=statechange NOT jobstart | search node="c0-0c1s6n1" | head 24 | getstate

#LOG_FILENAME = '/tmp/output_from_splunk_2.txt'
#logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG)

results = []
output_results = []
node_states = {}

def debug(msg):
#  logging.debug(msg)
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
  global output_results
  node = record['node']
  eventtype = record['eventtype']
  debug("Getting state node and event type ##########################")
  debug("Node: " + node)
  debug("Eventtype: " + eventtype)
  start_state, end_state = eventtype.split("-")
  debug("Start state from eventtype: " + start_state)
  debug("End state from eventtype: " + end_state)
  node_list = hostlist.expand_hostlist(node)
  new_node_list = []
  for single_node in node_list:
    current_state = get_current_state(single_node)
    debug("Current state from lookup: " + str(current_state))
    new_record = record
    new_record['node'] = single_node
    if current_state == start_state:
      new_record['state'] = end_state
    output_results.append(new_record)
    store_current_state(single_node, end_state)

def main():
  try:
    global results
    results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()

    # sort the results by time
    for r in sorted(results, key=lambda k: k['_time']):
      update_states(r)

  except:
    import traceback
    stack =  traceback.format_exc()
    results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

  splunk.Intersplunk.outputResults( output_results )


debug("Starting")
main()
debug("Finished")

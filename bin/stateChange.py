import sys,os,splunk.Intersplunk,hostlist,logging,ast,re,math

LOG_FILENAME = '/tmp/output_from_splunk_2.txt'
logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG)

# use double quotes to protect options when giving in search, eg:
#  tag=state | statechange "{'nodeField':'node', 'USR_Threshold':500}"
options = {'filter': True, 'nodeField':'nids', 'addAggregate': True}
trigger_options = {}
# USR and SYS should be integer(0.9*N) # where N is total system nodes
# ERR should be integer(0.01*N)+1      # "more than 1% of nodes"
# below is for cielito, where N=70
trigger_options = {'USR_Threshold':63, 'ERR_Threshold':8, 'SYS_Threshold':63}
results = []
output_results = []
node_states = {}
node_transitions = {}
known_states = []
counts = {}
thresholds = {}

# easy way to log data to LOG_FILENAME
def debug(msg):
  #logging.debug(msg)
  return

def debug2(msg):
  logging.debug(msg)
  return

##################################################################
def nodeStateChange(record, node, start_state, end_state):
    global counts
    node_states[node] = end_state
    new = {'_time': record.get('_time'),
           options.get('nodeField'): node,
           'nodeStateChange': start_state + "-" + end_state}
    for state in counts:
      new[state] = counts[state]
    output_results.append(new)

##################################################################
def updateCounts(record, state, delta):
  global thresholds, counts

  if counts.get(state) == None: # first time this state is seen
    counts[state] = 0
  before = counts[state]

  if delta > 0 or counts[state] > 0:
    counts[state] = counts[state] + delta

  if not thresholds.get(state) == None:
    new = {'_time': record.get('_time'),
           'systemStateChange': state}
    if   before < counts[state] and counts[state] == thresholds[state]:
      new['direction'] = "increasing"
      output_results.append(new)
    elif before > counts[state] and before        == thresholds[state]:
      new['direction'] = "decreasing"
      output_results.append(new)

##################################################################
def stateChangeLogic(record, nodes, start_state, end_state):
  global output_results, trigger_options, options, known_states, node_states
  if "-" in nodes or "[" in nodes:
    node_list = hostlist.expand_hostlist(nodes)
  else:
    node_list = nodes.split(",")
  debug("---- Working on: " + str(record))

  for node in node_list:
    current_state = node_states.get(node)
    if not current_state:                                                        # first seen
      updateCounts(record, end_state, 1)                           # increment
      nodeStateChange(record, node, "UNK", end_state)              # change
    elif current_state=="UNK" or start_state=="*" or current_state==start_state: # match
      updateCounts(record, current_state, -1)                      # decrement
      updateCounts(record, end_state, 1)                           # increment
      nodeStateChange(record, node, current_state, end_state)      # change

##################################################################
# derive state for given node and eventtype
# node can come in as a single node or list of nodes 
# the list of nodes can be in short (1-3) or long (1,2,3) form
# each node can have a different state or NOT a state at all
# only return the nodes that have a new state applied
def parseRecord(record, additional_details={}): #, last_eventtype):
  global output_results, options
  node = record.get(options.get('nodeField'))
  eventtype = record.get('eventtype')
  # if we don't have node or eventtype then skip
  if not eventtype or not node:
    return
  debug("Getting state node and event type ##########################")
  debug("Node: " + node)
  debug("Eventtype: " + eventtype)

  # eventtypes can come in with multiple values, i.e., "USR-ERR donna-ignore"
  # we will depend on the first to be statechange relevant (set via eventtype priority)
  eventtypes = eventtype.split(" ")
  # now get our start and end states
  if not eventtypes:
    return
  start_state, end_state = eventtypes[0].split("-")
  stateChangeLogic(record, node, start_state, end_state)


##################################################################
def nodeStateList(record):
  global node_states
  # make a list of nodes in each state
  stateList = {}
  for node in node_states:
    if stateList.get(node_states[node]) == None:
      stateList[node_states[node]] = []
    stateList[node_states[node]].append(node)

  # make new record
  new = {'_time': record.get('_time')}
  for state in stateList:
    new["StateName_"+state] = hostlist.collect_hostlist(stateList[state])

  output_results.append(new)


##################################################################
def main():
  global output_results
  try:
    global results, options, node_states, thresholds, trigger_options
    results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()

    # process arguments
    if len(sys.argv) > 1:
      new_options = ast.literal_eval(sys.argv[1])
      options.update(new_options)
      for k in filter(lambda x: re.match(".*_Threshold$", x), options.keys()):
        trigger_options[k] = options[k]

    # setup thresholds
    r = re.compile('(.+)_Threshold')
    for key in trigger_options:
      m = r.match(key)
      if not m == None:
        state = m.group(1)
        thresholds[state] = trigger_options[key]

    debug2("OPTIONS: " + str(options))
    
    i=0
    if len(results) and results[0].has_key('_time'):
      if results[0].get('_time') > results[-1].get('_time'):
        results = results[::-1]                     # ensure chronological order
      debug2("Starting on " + str(len(results)) + " events")
      last_record = None
      for r in results:
        i=i+1
        if i==1 and "StateName_" in r['_raw']: # does first record contain StateName?
          debug("Setting initial node states")
          p  = re.compile("(StateName_\w+)=")
          ps = re.compile("StateName_(\w+)")
          for stateName in p.findall(r['_raw']):
            mobj = ps.match(stateName)
            if not mobj == None:
              state = mobj.group(1)
              for node in hostlist.expand_hostlist(r.get(stateName)):
                node_states[node] = state			# save state
                if counts.get(state) == None:
                  counts[state] = 0					# seed counts
                counts[state] = counts[state] + 1	# increment counts
        else:
          # now update our record
          parseRecord(r)
          last_record = r
      if last_record!=None and options.get('addAggregate'):
        # need the last record for '_time' entry
        debug("AGGREGATE: Building aggregate event");
        nodeStateList(last_record)

  except:
    import traceback
    debug2("GTO HERE BAD")
    stack =  traceback.format_exc()
    debug2(str(stack))
    results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

  debug2("Outputting " + str(len(output_results)) + " events")
  splunk.Intersplunk.outputResults( output_results )


##################################################################
debug2("Starting")
main()
debug2("Finished")

import sys,os,splunk.Intersplunk,hostlist,logging,ast,re,math

LOG_FILENAME = '/tmp/splunk_stateChange_debug_log.txt'
logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG)

# use double quotes to protect options when giving in search, eg:
#  tag=state | statechange "{'nodeField':'node', 'USR_Threshold':500}"
options = {'filter': True, 'nodeField':'node', 'addAggregate': True}
results = []
output_results = []
node_states = {}
node_transitions = {}
known_states = []
counts = {}

# easy way to log data to LOG_FILENAME
def debug(msg):
  #logging.debug(msg)
  return

def debug2(msg):
  logging.debug(msg)
  return


##################################################################
def nodeStateChange(record, node, fromState, newState):
  global counts

  new = {            '_time'      : record.get('_time'),
                     'orig_index' : record.get('index'),
                     'host'       : node}

  # deal with fromState
  if fromState == None:                    # first time this node is seen
    fromState = "UNK"
  else:                                     # not first time
    new['oldState'] = fromState                     # note from state
    counts[fromState] = counts[fromState] - 1  # decrement count

  # deal with newState
  if counts.get(newState) == None:          # first time this state is seen
    counts[newState] = 0                         # initialize
  counts[newState] = counts[newState] + 1        # increment
  node_states[node] = newState                   # set state
  new['newState'] = newState                           # always note to state

  for state in counts:
    new[state+"Count"] = counts[state]              # note all state counts

  new['orig_event'] = record['_raw']               # include original message in output
  output_results.append(new)                # output new record


##################################################################
def stateChangeLogic(record, nodes, start_state, end_state):
  global output_results, options, known_states, node_states
  if "-" in nodes or "[" in nodes:
    node_list = hostlist.expand_hostlist(nodes)
  else:
    node_list = nodes.split(",")
  debug("---- Working on: " + str(record))

  if len(nodes) > 100:  # omit long node lists
      record['_raw'] = record['_raw'].replace(nodes,'(LONG_NODE_LIST)')

  for node in node_list:
    current_state = node_states.get(node)
    if current_state == None or current_state=="UNK" or start_state=="*" or current_state==start_state:
      nodeStateChange(record, node, current_state, end_state)


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
    global results, options, node_states
    results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()

    # process arguments
    if len(sys.argv) > 1:
      new_options = ast.literal_eval(sys.argv[1])
      options.update(new_options)

    debug2("OPTIONS: " + str(options))
    cosre  = re.compile("cos_(\w+)-(\w+)")
    
    i=0
    if len(results) and results[0].has_key('_time'):
      if results[0].get('_time') > results[-1].get('_time'):
        results = results[::-1]                     # ensure chronological order
      debug2("Starting on " + str(len(results)) + " events")
      last_record = None
      for r in results:
        i=i+1
        if i==1 and "StateName_" in r['_raw']: # does first record contain StateName?
          debug2("Setting initial node states")
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
          if i%1000 == 0:
            debug2("record " + str(i) + " of " + str(len(results)))

          # make sure we have needed fields
          node = r.get(options.get('nodeField')) or r.get('nids') or r.get('hosts')
          eventtype = r.get('eventtype')
          if eventtype and node:
            match = cosre.search(r['eventtype'])
            if match != None:
              # we do, so proceed
              start_state, end_state = match.groups()
              stateChangeLogic(r, node, start_state, end_state)
          last_record = r

      if last_record!=None and options.get('addAggregate'):
        # need the last record for '_time' entry
        debug("AGGREGATE: Building aggregate event");
        nodeStateList(last_record)

  except:
    import traceback
    debug2("SHOULD NOT GET HERE!!!")
    stack =  traceback.format_exc()
    debug2(str(stack))
    results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

  debug2("Outputting " + str(len(output_results)) + " events")
  splunk.Intersplunk.outputResults( output_results )


##################################################################
debug2("Starting")
main()
debug2("Finished\n\n")

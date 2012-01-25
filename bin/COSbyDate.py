import sys,os,splunk.Intersplunk,hostlist,logging,ast,re,math,time

LOG_FILENAME = '/tmp/splunk_COSbyDate_debug_log.txt'
logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG)

options = {'filter': True, 'nodeField':'node', 'addAggregate': True}
results = []
output_results = []

# easy way to log data to LOG_FILENAME
def debug(msg):
  logging.debug(msg)
  return

##################################################################
def main():
  global output_results
  secondsInADay = 24 * 3600
  # we only track 24 hours periods, starting with yesterday
  nowTime = time.localtime()
  secondsToday = nowTime.tm_hour*3600 + nowTime.tm_min*60 + nowTime.tm_sec
  LastTime = int(time.mktime(nowTime) - secondsToday - 1)

  try:
    global results, options, node_states
    results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()

    if len(results) and results[0].has_key('_time'):
      if results[0].get('_time') < results[-1].get('_time'):
        results = results[::-1] # ensure reverse chronological order
      debug("Starting on " + str(len(results)) + " events")

      # only track the first system seen;
      # a later version may track multiple systems
      index = results[1]['orig_index']
      psys = re.compile("hpc_(\w+)")
      mobj = psys.match(index)
      if not mobj == None:
        system = mobj.group(1)

      pstate = re.compile(system+"_(\w+)-(\w+)")
      DayBins = {} # create a dict
      Counts  = {} # create a dict
      DateSecs = {} # create a dict
      for r in results:
        rtime = int(r['_time'])
        if r['orig_index']==index and rtime <= LastTime: # only one system, and omit today
#          debug(r['_time']+" "+r['eventtype'])
          mobj = pstate.match(r['eventtype']) # assume that only one eventtype exists...
          if not mobj == None:
            state = mobj.group(2) # state transitioned to
            seconds = LastTime - rtime
            while seconds > 0: # every second counts
              date = time.strftime("%F", time.localtime(LastTime))
              endDate = time.strftime("%F", time.localtime(LastTime-seconds))

              # note the second beginning each day, for Splunk timeline rendering
              dateS = time.strptime(date+" 00:00:00", "%Y-%m-%d %H:%M:%S")
              DateSecs[date] = int(time.strftime("%s", dateS))

              # initialize
              if not date in DayBins:
                DayBins[date] = {} # create a dict
              if not state in DayBins[date]:
                DayBins[date][state] = 0 # create an int, ugh Python
              if not date in Counts:
                Counts[date] = {} # create a dict
              if not state in Counts[date]:
                Counts[date][state] = 0 # create an int, ugh Python

              # count the number of seconds in each state per day
              if endDate == date: # does not cross a date boundary
                DayBins[date][state] += seconds
                Counts[date][state] += 1 # count the number of state transitions per day
#                debug("ADDED "+str(seconds)+" to "+date+" "+state);
                seconds = 0
              else: # does cross a date boundary
                last_tm = time.localtime(LastTime)
                secs = last_tm.tm_hour*3600 + last_tm.tm_min*60 + last_tm.tm_sec
                DayBins[date][state] += secs
                LastTime -= secs+1
                seconds -= secs
#                debug("Added "+str(secs)+" to "+date+" "+state);
            LastTime = rtime

  except:
    import traceback
    debug("CAUGHT AN EXCEPTION!!!")
    stack =  traceback.format_exc()
    debug(str(stack))
    results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

#  debug(DayBins)
  # the last day is unlikely to be 24 hours - assume so and drop it
  dates = sorted(DayBins.keys())
  date = dates.pop(0)

  # ok, print em out
  for date in dates:
    new = { 'date'   : date }
    for state in DayBins[date]:
      new[state+"_hrs"] = round(float(DayBins[date][state])/3600,2)
      new[state+"_count"] = Counts[date][state]
      new['_time'] = DateSecs[date]
    output_results.append(new)
    
  debug("Outputting " + str(len(output_results)) + " events")
  splunk.Intersplunk.outputResults( output_results )


##################################################################
debug("Starting at " + time.asctime())
main()
debug("Finished at " + time.asctime() + "\n\n")

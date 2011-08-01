import sys,os,splunk.Intersplunk,logging

# Example:
# parameter passed to noInterpolate is in seconds
# tag=state NOT jobstart | stateChange "{'nodeField':'nid'}" | noInterpoloate 38000
# Or use the default time span of 1 day - 86400 seconds
# tag=state NOT jobstart | stateChange "{'nodeField':'nid'}" | noInterpoloate 

LOG_FILENAME = '/tmp/output_from_splunk_3.txt'
logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG)

# easy way to log data to LOG_FILENAME
def debug(msg):
  #logging.debug(msg)
  return

def main():
  output_results = []
  try:
    results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
    allowable_threshold = 86400 # seconds or 1 day

    if len(sys.argv) > 1:
      allowable_threshold = int(sys.argv[1])
    
    # sort the results by time

    if len(results):
      last_record = None
      for r in results:
        ############ BEGIN INTERPOLATION #################
        # add interpolation records to fill the gap between records
        if allowable_threshold > 0 and last_record:
          diff_time = int(r.get('_time')) - int(last_record.get('_time'))
          # if the gap between the current event and the last event is > the allowable time threshold
          # then we add an event a gaps length from the current event
          if diff_time > allowable_threshold:
            interpolation_record = last_record.copy()
            current_record_time = r.get('_time')
            # we need to add events every eventInterpolation value to fill the gap
            interpolation_record['_time'] = int(current_record_time) - 1
            interpolation_record['interpolationRecord'] = 'yes'
            if interpolation_record not in output_results:
              output_results.append(interpolation_record)
        ############ END INTERPOLATION #################
        last_record = r
        output_results.append(r)

  except:
    import traceback
    stack =  traceback.format_exc()
    results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

  splunk.Intersplunk.outputResults( output_results )

debug("Starting")
main()
debug("Finished")

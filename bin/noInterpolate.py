import sys,os,splunk.Intersplunk,logging

# Example: 
# tag=state NOT jobstart | stateChange "{'nodeField':'nid'}" | noInterpoloate 38000

LOG_FILENAME = '/tmp/output_from_splunk_3.txt'
logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG)

# easy way to log data to LOG_FILENAME
def debug(msg):
  #logging.debug(msg)
  return

def get_sorted_results(results):
  if len(results) and results[0].has_key('_time'):
    return sorted(results, key=lambda k: k['_time'])
  else:
    return results

def main():
  output_results = []
  try:
    results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
    allowable_threshold = 86400 # seconds or 1 day

    if len(sys.argv) > 1:
      allowable_threshold = int(sys.argv[1])
    
    # sort the results by time
    sorted_results = get_sorted_results(results)

    debug(len(sorted_results))

    if len(sorted_results):
      last_record = None
      for r in sorted_results:
        ############ BEGIN INTERPOLATION #################
        # add interpolation records to fill the gap between records
        if allowable_threshold > 0 and last_record:
          diff_time = int(r.get('_time')) - int(last_record.get('_time'))
          # if the gap between the current event and the last event is > the allowable time threshold
          # then we add an event a gaps length from the current event
          if diff_time > allowable_threshold:
            interpolation_record = last_record
            current_record_time = r.get('_time')
            # we need to add events every eventInterpolation value to fill the gap
            interpolation_record['_time'] = int(current_record_time) - allowable_threshold
            interpolation_record['interpolationRecord'] = 'yes'
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

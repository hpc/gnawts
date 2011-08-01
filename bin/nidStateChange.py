import csv
import sys
import logging

# receives _time, nid, from and to fields in that order
# if input "from" does not contain a previous state for nid, then skip that record
# 

# from ticket #25 in redmine
# 1)  it should use raw csv in/out instead of intersplunk
# 2)  it should perform only the state change logic
# 3)  the field set coming in will be:  _time, nid, from, and to (in order)
# 4)  if the input event does not cause a state change 
#     (input from does not match known state), do not copy it to output. 
# 5)  if it does cause a state change, copy it to output
# 6)  if this is the first event seen for this nid, set the from field to be null
# 7)  if the input from field is null (eg -RSV per #22) and you know what 
#     the previous state of the node is, set the output value accordingly.
LOG_FILENAME = '/tmp/output_from_splunk_2.txt'
logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG)

# easy way to log data to LOG_FILENAME
def debug(msg):
  #logging.debug(msg)
  return

node_states = {}

def main():
  try:
    # 1)
    r = csv.reader(sys.stdin)

    first  = True
    writer = csv.writer(sys.stdout, quoting=csv.QUOTE_ALL)
    #writer = csv.writer(open('test.csv', 'wb'), quoting=csv.QUOTE_ALL)

    # 2)
    nodeStateChangeField = "nodeStateChange"

    # 3) 
    # fields come in this order : _time, nid, from, to
    _time         = 0
    _nid          = 1
    _from         = 2
    _to           = 3

    for l in r:
      if first:
        header = [l[_time], l[_nid], l[_from], l[_to]]
        header.append(nodeStateChangeField)
        first  = False
        writer.writerow(header)
        continue
      
      known_previous_state = node_states.get(l[_nid])

      # 4)
      # skip if "from" does not match last known state for nid
      if known_previous_state and known_previous_state != l[_from]:
        continue

      # 7)
      # if known_previous_state for nid exists and _from is None, set it
      if l[_from] == None or l[_from] == "":
        l[_from] = known_previous_state 

      # 6)
      # if nid has no last known state then "from" is Null
      if known_previous_state == None:
        l[_from] = None 

      # 2) only perform state change logic
      # 5) 
      # if state change occurs output the record
      # set the node_state for this nid to the to
      node_states[l[_nid]] = l[_to]
      # result contains state change
      new_l = [l[_time], l[_nid], l[_from], l[_to]]
      new_l.append(str(l[_from]) + "-" + str(l[_to]))

      # 1)
      writer.writerow(new_l)
  except:
    import traceback
    debug("GOT HERE BAD")
    debug(traceback.format_exc())

debug("STARTING")
main()
debug("FINISHING")

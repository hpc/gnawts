import csv
import sys

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

node_states = {}

def main():
  # 1)
  r = csv.reader(sys.stdin)

  header = []
  first  = True
  writer = None

  # 2)
  nodeStateChangeField = "nodeStateChange"

  # 3) 
  # fields come in this order : _time, nid, from, to
  _time         = 0
  _nid          = 1
  _from         = 2
  _to           = 3
  _state_change = 4

  for l in r:
    if first:
      header = l
      header.append(nodeStateChangeField)
      first  = False
      csv.writer(sys.stdout).writerow(header)
      writer = csv.DictWriter(sys.stdout, header)
      continue
    
    known_previous_state = node_states.get(r[_nid])

    # 4)
    # skip if "from" does not match last known state for nid
    if known_previous_state and known_previous_state != r[_from]:
      continue

    # 7)
    # if known_previous_state for nid exists and _from is None, set it
    if r[_from] == None or r[_from] == "":
      r[_from] = known_previous_state 

    # 6)
    # if nid has no last known state then "from" is Null
    if known_previous_state == None:
      r[_from] = None 

    # 2) only perform state change logic
    # 5) 
    # if state change occurs output the record
    # set the node_state for this nid to the to
    node_states[r[_nid]] = r[_to]
    # result contains state change
    r[_state_change] = str(r[_from]) + "-" + str(r[_to])

    # 1)
    writer.writerow(r)

main()

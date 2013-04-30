import sys, unittest
sys.path.append('../bin')

sample_input_1 = open('sample_input_from_splunk_1.csv', 'r')
sample_input_2 = open('sample_input_from_splunk_2.csv', 'r')
sys.stdin = sample_input_1
import stateChange

class RSVSTARTTestCase(unittest.TestCase):
  def setUp(self):
    # for these tests, we expect some input from Splunk
    sys.stdin = sample_input_1
    stateChange.node_states = {}
    stateChange.node_trasitions = {}
    stateChange.output_results = []
    stateChange.trigger_options = {}

  def test_state_change_for_simple_set(self):
    stateChange.trigger_options['-SYS_Threshold'] = 2
    stateChange.trigger_options['USR-ERR_Threshold'] = 1
    stateChange.update_output_results_for_node({'_time':'1', 'nids':'n1'}, 'n1', 'USR', 'ERR')
    stateChange.update_output_results_for_node({'_time':'2', 'nids':'n2'}, 'n5', '*', 'SYS')
    stateChange.update_output_results_for_node({'_time':'3', 'nids':'n6'}, 'n6', '*', 'SYS')
    self.assertEqual(stateChange.output_results[1],  {'_time':'1', 'systemStateChange':'USR-ERR', 'crossing': 'increasing'})
    self.assertEqual(stateChange.output_results[-1], {'_time':'3', 'systemStateChange':'UNK-SYS', 'crossing': 'increasing'})
  
  def test_state_change_for_simple_set2(self):
    #    return # IGNORE FOR NOW, but would be nice to base thresholds on a single state rather than transition
    stateChange.trigger_options['SYS_Threshold'] = 2
    stateChange.update_output_results_for_node({'_time':'1', 'nids':'n1'}, 'n1', 'USR', 'ERR')
    stateChange.update_output_results_for_node({'_time':'2', 'nids':'n2'}, 'n5', 'USR', 'SYS')
    stateChange.update_output_results_for_node({'_time':'3', 'nids':'n6'}, 'n6', 'ERR', 'SYS')
    self.assertEqual(stateChange.output_results[-1], {'_time':'3', 'systemStateChange':'SYS', 'crossing': 'increasing'})


class TriggerEventsTestCase(unittest.TestCase):
  def setUp(self):
    # for these tests, we expect some input from Splunk
    sys.stdin = sample_input_1
    stateChange.node_states = {}
    stateChange.node_trasitions = {}
    stateChange.output_results = []
    stateChange.trigger_options = {}

  def test_state_change_for_simple_set(self):
    stateChange.trigger_options['SYS-ERR_Threshold'] = 2
    stateChange.update_output_results_for_node({'_time':'1', 'nids':'n1'}, 'n1', 'USR', 'SYS')
    stateChange.update_output_results_for_node({'_time':'2', 'nids':'n2'}, 'n5', 'SYS', 'ERR')
    stateChange.update_output_results_for_node({'_time':'3', 'nids':'n6'}, 'n6', 'SYS', 'ERR')
    self.assertEqual(stateChange.output_results[-1], {'_time':'3', 'systemStateChange':'SYS-ERR', 'crossing': 'increasing'})
  
  def test_state_change_for_more_complex_set(self):
    stateChange.trigger_options['SYS-ERR_Threshold'] = 2
    stateChange.trigger_options['ERR-USR_Threshold'] = 3
    stateChange.update_output_results_for_node({'_time':'1', 'nids':'n1'}, 'n1', 'USR', 'SYS')
    stateChange.update_output_results_for_node({'_time':'2', 'nids':'n5'}, 'n5', 'SYS', 'ERR') # + 1 for sys-err
    stateChange.update_output_results_for_node({'_time':'3', 'nids':'n6'}, 'n6', 'SYS', 'ERR') # + 1 for sys-err trigger up for sys-err
    stateChange.update_output_results_for_node({'_time':'4', 'nids':'n5'}, 'n5', 'ERR', 'USR') # - 1 for sys-err, + 1 for err-usr, trigger down for sys-err
    stateChange.update_output_results_for_node({'_time':'5', 'nids':'n6'}, 'n6', 'ERR', 'USR') # + 1 for err-usr
    stateChange.update_output_results_for_node({'_time':'6', 'nids':'n7'}, 'n7', 'ERR', 'USR') # + 1 for err-usr, trigger up for err-usr
    stateChange.update_output_results_for_node({'_time':'7', 'nids':'n8'}, 'n8', 'ERR', 'USR') # + 1 for err-usr
    self.assertTrue({'_time':'3', 'systemStateChange':'SYS-ERR', 'crossing': 'increasing'} in stateChange.output_results)
    self.assertTrue({'_time':'4', 'systemStateChange':'SYS-ERR', 'crossing': 'decreasing'} in stateChange.output_results)
    self.assertTrue({'_time':'6', 'systemStateChange':'ERR-USR', 'crossing': 'increasing'} in stateChange.output_results)
    self.assertTrue({'_time':'3', 'nids':'n6', 'nodeStateChange': 'SYS-ERR', 'ERR':2, 'SYS':0} in stateChange.output_results)
    self.assertTrue({'_time':'4', 'nids':'n5', 'nodeStateChange': 'ERR-USR', 'USR':1, 'ERR':1} in stateChange.output_results)
    self.assertTrue({'_time':'6', 'nids':'n7', 'nodeStateChange': 'ERR-USR', 'USR':3, 'ERR':0} in stateChange.output_results)

class AggregateEventsTestCase(unittest.TestCase):
  def setUp(self):
    # for these tests, we expect some input from Splunk
    sys.stdin = sample_input_1
    stateChange.node_states = {}
    stateChange.output_results = []
  
  def test_output_results_should_contain_an_aggregate_event(self):
    # record, node, start_state, end_state
    stateChange.update_output_results_for_node({'_time':'1', 'nids':'n1'}, 'n1', 'USR', 'SYS')
    stateChange.update_output_results_for_node({'_time':'1', 'nids':'n2'}, 'n2', 'USR', 'ERR')
    stateChange.build_aggregate_event({'_time':'1'})
    self.assertEqual(stateChange.output_results[-1], {'_time':'1', 'eventtype':'nodeStateList', 'StateName_SYS':'n1', 'StateName_ERR': 'n2'})
  
  def test_more_complicated_output_results_should_contain_an_aggregate_event(self):
    # record, node, start_state, end_state
    stateChange.update_output_results_for_node({'_time':'1', 'nids':'n1'}, 'n1', 'USR', 'SYS')
    stateChange.update_output_results_for_node({'_time':'1', 'nids':'n2'}, 'n2', 'USR', 'ERR')
    stateChange.update_output_results_for_node({'_time':'1', 'nids':'n2'}, 'n3', 'USR', 'ERR')
    stateChange.update_output_results_for_node({'_time':'1', 'nids':'n2'}, 'n4', 'USR', 'ERR')
    stateChange.update_output_results_for_node({'_time':'1', 'nids':'n2'}, 'n5', 'USR', 'SYS')
    stateChange.update_output_results_for_node({'_time':'1', 'nids':'n2'}, 'n6', 'USR', 'SYS')
    stateChange.build_aggregate_event({'_time':'1'})
    self.assertEqual(stateChange.output_results[-1], {'_time':'1', 'eventtype':'nodeStateList', 'StateName_SYS':'n[1,5-6]', 'StateName_ERR': 'n[2-4]'})

class DefaultStateTestCase(unittest.TestCase):

  def setUp(self):
    # for these tests, we expect some input from Splunk
    sys.stdin = sample_input_1
    stateChange.node_states = {}
    stateChange.output_results = []
    stateChange.options['addAggregate'] = False

  def test_store_current_state(self):
    self.assertEqual(stateChange.node_states, {})
    stateChange.store_current_state('n1', 'ERR')
    self.assertEqual(stateChange.node_states, {'n1':'ERR'})
  
  def test_get_current_state(self):
    self.assertEqual(stateChange.node_states, {})
    stateChange.store_current_state('n1', 'ERR')
    self.assertEqual(stateChange.get_current_state('n1'), 'ERR')

  def test_get_current_state_with_does_not_exist(self):
    self.assertEqual(stateChange.node_states, {})
    stateChange.store_current_state('n1', 'ERR')
    self.assertEqual(stateChange.get_current_state('n2'), None)

  def test_update_output_results_should_produce_output_since_state_is_assumed(self):
    self.assertEqual(stateChange.output_results, [])
    # record, node, start_state, end_state
    stateChange.update_output_results_for_node({'nids':'n1'}, 'n1', 'USR', 'SYS')
    self.assertEqual(stateChange.output_results, [{'nids':'n1', '_time': None, 'nodeStateChange':'USR-SYS', 'SYS':1, 'USR':0}])
  
  def test_update_output_results_should_produce_output_since_state_is_assumed_2(self):
    self.assertEqual(stateChange.output_results, [])
    # record, node, start_state, end_state
    stateChange.update_output_results_for_node({'nids':'n1'}, 'n1', 'USR', 'SYS')
    self.assertEqual(stateChange.output_results, [{'nids':'n1', '_time': None, 'nodeStateChange':'USR-SYS', 'SYS':1, 'USR':0}])
  
  def test_update_output_results_should_produce_output_only_if_state_changed_or_has_to_be_assumed(self):
    self.assertEqual(stateChange.output_results, [])
    # record, node, start_state, end_state
    stateChange.update_output_results_for_node({'nids':'n1'}, 'n1', 'USR', 'SYS')
    stateChange.update_output_results_for_node({'nids':'n2'}, 'n2', 'USR', 'SYS')
    stateChange.update_output_results_for_node({'nids':'n1'}, 'n1', 'USR', 'SYS')
    stateChange.update_output_results_for_node({'nids':'n2'}, 'n2', 'SYS', 'ERR')
    self.assertEqual(stateChange.output_results, [{'nids':'n1', '_time': None, 'nodeStateChange':'USR-SYS', 'SYS':1, 'USR':0}, {'nids':'n2', '_time': None, 'nodeStateChange':'USR-SYS', 'SYS':2, 'USR':0}, {'nids':'n2', '_time': None, 'nodeStateChange':'SYS-ERR', 'ERR':1, 'SYS':1}])
  
    
# run the tests
suite1 = unittest.TestLoader().loadTestsFromTestCase(DefaultStateTestCase)
suite2 = unittest.TestLoader().loadTestsFromTestCase(AggregateEventsTestCase)
suite3 = unittest.TestLoader().loadTestsFromTestCase(TriggerEventsTestCase)
suite4 = unittest.TestLoader().loadTestsFromTestCase(RSVSTARTTestCase)
#unittest.TextTestRunner(verbosity=2).run(suite1)
#unittest.TextTestRunner(verbosity=2).run(suite2)
#unittest.TextTestRunner(verbosity=2).run(suite3)
unittest.TextTestRunner(verbosity=2).run(suite4)


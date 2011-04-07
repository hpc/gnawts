import sys, unittest
sys.path.append('../bin')

sample_input_1 = open('sample_input_from_splunk_1.csv', 'r')
sample_input_2 = open('sample_input_from_splunk_2.csv', 'r')
sys.stdin = sample_input_1
import stateChange


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
    stateChange.update_output_results_for_node({'_time':'1', 'node':'n1'}, 'n1', 'USR', 'SYS')
    stateChange.update_output_results_for_node({'_time':'2', 'node':'n2'}, 'n5', 'SYS', 'ERR')
    stateChange.update_output_results_for_node({'_time':'3', 'node':'n2'}, 'n6', 'SYS', 'ERR')
    self.assertEqual(stateChange.output_results[-1], {'_time':'3', 'systemStateChange':'SYS-ERR', 'crossing': 'upward'})
  
  def test_state_change_for_more_complex_set(self):
    stateChange.trigger_options['SYS-ERR_Threshold'] = 2
    stateChange.trigger_options['ERR-USR_Threshold'] = 3
    stateChange.update_output_results_for_node({'_time':'1', 'node':'n1'}, 'n1', 'USR', 'SYS')
    stateChange.update_output_results_for_node({'_time':'2', 'node':'n2'}, 'n5', 'SYS', 'ERR') # + 1 for sys-err
    stateChange.update_output_results_for_node({'_time':'3', 'node':'n2'}, 'n6', 'SYS', 'ERR') # + 1 for sys-err trigger up for sys-err
    stateChange.update_output_results_for_node({'_time':'4', 'node':'n5'}, 'n5', 'ERR', 'USR') # - 1 for sys-err, + 1 for err-usr, trigger down for sys-err
    stateChange.update_output_results_for_node({'_time':'5', 'node':'n6'}, 'n6', 'ERR', 'USR') # + 1 for err-usr
    stateChange.update_output_results_for_node({'_time':'6', 'node':'n7'}, 'n7', 'ERR', 'USR') # + 1 for err-usr, trigger up for err-usr
    stateChange.update_output_results_for_node({'_time':'7', 'node':'n8'}, 'n8', 'ERR', 'USR') # + 1 for err-usr
    self.assertTrue({'_time':'3', 'systemStateChange':'SYS-ERR', 'crossing': 'upward'} in stateChange.output_results)
    self.assertTrue({'_time':'4', 'systemStateChange':'SYS-ERR', 'crossing': 'downward'} in stateChange.output_results)
    self.assertTrue({'_time':'6', 'systemStateChange':'ERR-USR', 'crossing': 'upward'} in stateChange.output_results)

class AggregateEventsTestCase(unittest.TestCase):
  def setUp(self):
    # for these tests, we expect some input from Splunk
    sys.stdin = sample_input_1
    stateChange.node_states = {}
    stateChange.output_results = []
  
  def test_output_results_should_contain_an_aggregate_event(self):
    # record, node, start_state, end_state
    stateChange.update_output_results_for_node({'_time':'1', 'node':'n1'}, 'n1', 'USR', 'SYS')
    stateChange.update_output_results_for_node({'_time':'1', 'node':'n2'}, 'n2', 'USR', 'ERR')
    stateChange.build_aggregate_event({'_time':'1'})
    self.assertEqual(stateChange.output_results[-1], {'_time':'1', 'eventtype':'nodeStateList', 'SYS':'n1', 'ERR': 'n2'})
  
  def test_more_complicated_output_results_should_contain_an_aggregate_event(self):
    # record, node, start_state, end_state
    stateChange.update_output_results_for_node({'_time':'1', 'node':'n1'}, 'n1', 'USR', 'SYS')
    stateChange.update_output_results_for_node({'_time':'1', 'node':'n2'}, 'n2', 'USR', 'ERR')
    stateChange.update_output_results_for_node({'_time':'1', 'node':'n2'}, 'n3', 'USR', 'ERR')
    stateChange.update_output_results_for_node({'_time':'1', 'node':'n2'}, 'n4', 'USR', 'ERR')
    stateChange.update_output_results_for_node({'_time':'1', 'node':'n2'}, 'n5', 'USR', 'SYS')
    stateChange.update_output_results_for_node({'_time':'1', 'node':'n2'}, 'n6', 'USR', 'SYS')
    stateChange.build_aggregate_event({'_time':'1'})
    self.assertEqual(stateChange.output_results[-1], {'_time':'1', 'eventtype':'nodeStateList', 'SYS':'n[1,5-6]', 'ERR': 'n[2-4]'})

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
    stateChange.update_output_results_for_node({'node':'n1'}, 'n1', 'USR', 'SYS')
    self.assertEqual(stateChange.output_results, [{'node':'n1', 'nodeStateTransition':'USR-SYS'}])
  
  def test_update_output_results_should_produce_output_since_state_is_assumed_2(self):
    self.assertEqual(stateChange.output_results, [])
    # record, node, start_state, end_state
    stateChange.update_output_results_for_node({'node':'n1'}, 'n1', 'USR', 'SYS')
    self.assertEqual(stateChange.output_results, [{'node':'n1', 'nodeStateTransition':'USR-SYS'}])
  
  def test_update_output_results_should_produce_output_only_if_state_changed_or_has_to_be_assumed(self):
    self.assertEqual(stateChange.output_results, [])
    # record, node, start_state, end_state
    stateChange.update_output_results_for_node({'node':'n1'}, 'n1', 'USR', 'SYS')
    stateChange.update_output_results_for_node({'node':'n2'}, 'n2', 'USR', 'SYS')
    stateChange.update_output_results_for_node({'node':'n1'}, 'n1', 'USR', 'SYS')
    stateChange.update_output_results_for_node({'node':'n2'}, 'n2', 'SYS', 'ERR')
    self.assertEqual(stateChange.output_results, [{'node':'n1', 'nodeStateTransition':'USR-SYS'}, {'node':'n2', 'nodeStateTransition':'USR-SYS'}, {'node':'n2', 'nodeStateTransition':'SYS-ERR'}])
  
    
# run the tests
suite1 = unittest.TestLoader().loadTestsFromTestCase(DefaultStateTestCase)
suite2 = unittest.TestLoader().loadTestsFromTestCase(AggregateEventsTestCase)
suite3 = unittest.TestLoader().loadTestsFromTestCase(TriggerEventsTestCase)
unittest.TextTestRunner(verbosity=2).run(suite1)
unittest.TextTestRunner(verbosity=2).run(suite2)
unittest.TextTestRunner(verbosity=2).run(suite3)


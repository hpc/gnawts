import sys, unittest
sys.path.append('../bin')

sample_input_1 = open('sample_input_from_splunk_1.csv', 'r')
sample_input_2 = open('sample_input_from_splunk_2.csv', 'r')
sys.stdin = sample_input_1
import getState


class DefaultStateTestCase(unittest.TestCase):

  def setUp(self):
    # for these tests, we expect some input from Splunk
    sys.stdin = sample_input_1
    getState.node_states = {}
    getState.output_results = []

  def test_store_current_state(self):
    self.assertEqual(getState.node_states, {})
    getState.store_current_state('n1', 'ERR')
    self.assertEqual(getState.node_states, {'n1':'ERR'})
  
  def test_get_current_state(self):
    self.assertEqual(getState.node_states, {})
    getState.store_current_state('n1', 'ERR')
    self.assertEqual(getState.get_current_state('n1'), 'ERR')

  def test_get_current_state_with_does_not_exist(self):
    self.assertEqual(getState.node_states, {})
    getState.store_current_state('n1', 'ERR')
    self.assertEqual(getState.get_current_state('n2'), None)

  def test_update_output_results_should_produce_output_since_state_is_assumed(self):
    self.assertEqual(getState.output_results, [])
    # record, node, current_state, start_state, end_state
    getState.update_output_results_for_node({'node':'n1'}, 'n1', 'ERR', 'USR', 'SYS')
    self.assertEqual(getState.output_results, [{'node':'n1', 'state':'SYS'}])
  
  def test_update_output_results_should_produce_output_since_state_is_assumed_2(self):
    self.assertEqual(getState.output_results, [])
    # record, node, current_state, start_state, end_state
    getState.update_output_results_for_node({'node':'n1'}, 'n1', 'USR', 'USR', 'SYS')
    self.assertEqual(getState.output_results, [{'node':'n1', 'state':'SYS'}])
  
  def test_update_output_results_should_produce_output_only_if_state_changed_or_has_to_be_assumed(self):
    self.assertEqual(getState.output_results, [])
    # record, node, current_state, start_state, end_state
    getState.update_output_results_for_node({'node':'n1'}, 'n1', 'USR', 'USR', 'SYS')
    getState.update_output_results_for_node({'node':'n2'}, 'n2', 'USR', 'USR', 'SYS')
    getState.update_output_results_for_node({'node':'n1'}, 'n1', 'SYS', 'USR', 'SYS')
    getState.update_output_results_for_node({'node':'n2'}, 'n2', 'SYS', 'SYS', 'ERR')
    self.assertEqual(getState.output_results, [{'node':'n1', 'state':'SYS'}, {'node':'n2', 'state':'SYS'}, {'node':'n2', 'state':'ERR'}])
  
    
# run the tests
suite = unittest.TestLoader().loadTestsFromTestCase(DefaultStateTestCase)
unittest.TextTestRunner(verbosity=2).run(suite)


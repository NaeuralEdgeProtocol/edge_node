"""
This plugin is used to synchronize the availability tables between the oracles.
Initially thought as a way to synchronize the last availability table, it was 
extended to synchronize the availability tables for all epochs.

This plugin works with a state machine, to better separate the different stages of the sync process.
It works as follows:

On connection, the plugin requests the availability tables for its missing epochs from the online oracles.
Then, in a loop
0. Wait for the epoch to change
1. Compute the local table of availability
  - if the node cannot participate in the sync process, it will request the availability table from the other oracles
  - otherwise, it will continue to the next stage
2. Exchange the local table of availability between oracles
3. Compute the median table of availability, based on the local tables received from the oracles 
  - for each node in the table, compute the median value and sign it
4. Exchange the median table of availability between oracles
5. Compute the agreed median table of availability, based on the median tables received from the oracles
  - for each node in the table, compute the most frequent median value and collect the signatures
6. Exchange the agreed median table of availability between oracles
7. Update the epoch manager with the agreed median table
Jump to 0

Pipeline config:
{
  "NAME": "oracle_sync",
  "PLUGINS": [
    {
      "INSTANCES": [
        {
          "INSTANCE_ID": "default",
        }
      ],
      "SIGNATURE": "ORACLE_SYNC_01"
    }
  ],
  "TYPE": "NetworkListener",
  "PATH_FILTER" : [None, None, "ORACLE_SYNC_01", None],
  "MESSAGE_FILTER" : {},
}


To deploy for the first time:
1. Set `last_epoch_synced = X-1` in epoch manager
2. Start boxes in epoch X-1, let them run through epoch X-1, and let them enter in epoch X
3. During epoch X, deploy the plugin on all oracles
4. The plugins will skip the first sync process, because current epoch (X)
   is the same as the last epoch synced (X-1) + 1
4. Let all oracles run through epoch X, until they enter epoch X+1
5. When they enter epoch X+1, the plugin will start the sync process
"""

from naeural_core.business.base import BasePluginExecutor as BaseClass

_CONFIG = {
  **BaseClass.CONFIG,

  # Jobs should have a bigger inputs queue size, because they have to process everything
  'MAX_INPUTS_QUEUE_SIZE': 500,

  # Allow empty inputs in order to send pings from time to time
  'ALLOW_EMPTY_INPUTS': True,
  'PROCESS_DELAY': 0,

  'SEND_PERIOD': 10,  # seconds
  'SEND_INTERVAL': 5,  # seconds

  'EPOCH_START_SYNC': 0,

  'VALIDATION_RULES': {
    **BaseClass.CONFIG['VALIDATION_RULES'],
  },
}

__VER__ = '0.1.0'


class OracleSync01Plugin(BaseClass):

  class STATES:
    S0_WAIT_FOR_EPOCH_CHANGE = 'WAIT_FOR_EPOCH_CHANGE'
    S1_COMPUTE_LOCAL_TABLE = 'COMPUTE_LOCAL_TABLE'
    S2_SEND_LOCAL_TABLE = 'SEND_LOCAL_TABLE'
    S3_COMPUTE_MEDIAN_TABLE = 'COMPUTE_MEDIAN_TABLE'
    S4_SEND_MEDIAN_TABLE = 'SEND_MEDIAN_TABLE'
    S5_COMPUTE_AGREED_MEDIAN_TABLE = 'COMPUTE_AGREED_MEDIAN_TABLE'
    S6_SEND_AGREED_MEDIAN_TABLE = 'SEND_AGREED_MEDIAN_TABLE'
    S7_UPDATE_EPOCH_MANAGER = 'UPDATE_EPOCH_MANAGER'
    S8_SEND_REQUEST_AGREED_MEDIAN_TABLE = 'SEND_REQUEST_AGREED_MEDIAN_TABLE'
    S9_COMPUTE_REQUESTED_AGREED_MEDIAN_TABLE = 'COMPUTE_REQUESTED_AGREED_MEDIAN_TABLE'

  def on_init(self):
    self.__reset_to_initial_state()

    # All oracles start in the state S7_WAIT_FOR_ORACLE_SYNC
    # because they have to wait to receive the agreed median table from the previous epoch
    self.state_machine_name = 'OracleSyncPlugin'
    self.state_machine_api_init(
      name=self.state_machine_name,
      state_machine_transitions=self._prepare_job_state_transition_map(),
      initial_state=self.STATES.S8_SEND_REQUEST_AGREED_MEDIAN_TABLE,
      on_successful_step_callback=self.state_machine_api_callback_do_nothing,
    )
    return

  # State machine callbacks
  if True:
    def _prepare_job_state_transition_map(self):
      job_state_transition_map = {
        self.STATES.S0_WAIT_FOR_EPOCH_CHANGE: {
          'STATE_CALLBACK': self.__receive_requests_from_oracles_and_send_responses,
          'DESCRIPTION': "Wait for the epoch to change",
          'TRANSITIONS': [
            {
              'NEXT_STATE': self.STATES.S1_COMPUTE_LOCAL_TABLE,
              'TRANSITION_CONDITION': self.__epoch_finished,
              'ON_TRANSITION_CALLBACK': self.state_machine_api_callback_do_nothing,
              'DESCRIPTION': "If the epoch has changed, compute the local table of availability",
            },
          ],
        },
        self.STATES.S1_COMPUTE_LOCAL_TABLE: {
          'STATE_CALLBACK': self.__compute_local_table,
          'DESCRIPTION': "Compute the local table of availability",
          'TRANSITIONS': [
            {
              'NEXT_STATE': self.STATES.S2_SEND_LOCAL_TABLE,
              'TRANSITION_CONDITION': self.__can_participate_in_sync,
              'ON_TRANSITION_CALLBACK': self.state_machine_api_callback_do_nothing,
              'DESCRIPTION': "If the node can participate, join the sync process",
            },
            {
              'NEXT_STATE': self.STATES.S8_SEND_REQUEST_AGREED_MEDIAN_TABLE,
              'TRANSITION_CONDITION': self.__cannot_participate_in_sync,
              'ON_TRANSITION_CALLBACK': self.state_machine_api_callback_do_nothing,
              'DESCRIPTION': "If the node cannot participate, periodically request the agreed median table from the oracles",
            }
          ],
        },
        self.STATES.S2_SEND_LOCAL_TABLE: {
          'STATE_CALLBACK': self.__receive_local_table_and_maybe_send_local_table,
          'DESCRIPTION': "Exchange local table of availability between oracles",
          'TRANSITIONS': [
            {
              'NEXT_STATE': self.STATES.S3_COMPUTE_MEDIAN_TABLE,
              'TRANSITION_CONDITION': self.__send_local_table_timeout,
              'ON_TRANSITION_CALLBACK': self.state_machine_api_callback_do_nothing,
              'DESCRIPTION': "After the exchange phase time expires, compute the median table",
            }
          ],
        },
        self.STATES.S3_COMPUTE_MEDIAN_TABLE: {
          'STATE_CALLBACK': self.__compute_median_table,
          'DESCRIPTION': "Compute the median table of availability, based on the local tables received from the oracles",
          'TRANSITIONS': [
            {
              'NEXT_STATE': self.STATES.S4_SEND_MEDIAN_TABLE,
              'TRANSITION_CONDITION': self.state_machine_api_callback_always_true,
              'ON_TRANSITION_CALLBACK': self.state_machine_api_callback_do_nothing,
              'DESCRIPTION': "Begin the exchange process of the median tables between oracles",
            }
          ],
        },
        self.STATES.S4_SEND_MEDIAN_TABLE: {
          'STATE_CALLBACK': self.__receive_median_table_and_maybe_send_median_table,
          'DESCRIPTION': "Exchange median table of availability between oracles",
          'TRANSITIONS': [
            {
              'NEXT_STATE': self.STATES.S5_COMPUTE_AGREED_MEDIAN_TABLE,
              'TRANSITION_CONDITION': self.__send_median_table_timeout,
              'ON_TRANSITION_CALLBACK': self.state_machine_api_callback_do_nothing,
              'DESCRIPTION': "After the exchange phase time expires, compute the agreed median table",
            },
          ],
        },
        self.STATES.S5_COMPUTE_AGREED_MEDIAN_TABLE: {
          'STATE_CALLBACK': self.__compute_agreed_median_table,
          'DESCRIPTION': "Compute the agreed median table of availability, based on the median tables received from the oracles",
          'TRANSITIONS': [
            {
              'NEXT_STATE': self.STATES.S6_SEND_AGREED_MEDIAN_TABLE,
              'TRANSITION_CONDITION': self.state_machine_api_callback_always_true,
              'ON_TRANSITION_CALLBACK': self.state_machine_api_callback_do_nothing,
              'DESCRIPTION': "Begin the exchange process of the agreed median tables between oracles",
            }
          ],
        },
        self.STATES.S6_SEND_AGREED_MEDIAN_TABLE: {
          'STATE_CALLBACK': self.__receive_agreed_median_table_and_maybe_send_agreed_median_table,
          'DESCRIPTION': "Exchange agreed median table of availability between oracles",
          'TRANSITIONS': [
            {
              'NEXT_STATE': self.STATES.S7_UPDATE_EPOCH_MANAGER,
              'TRANSITION_CONDITION': self.__send_agreed_value_timeout,
              'ON_TRANSITION_CALLBACK': self.__reset_to_initial_state,
              'DESCRIPTION': "After the exchange phase time expires, update the epoch manager with the agreed median table",
            }
          ],
        },
        self.STATES.S7_UPDATE_EPOCH_MANAGER: {
          'STATE_CALLBACK': self.__update_epoch_manager_with_agreed_median_table,
          'DESCRIPTION': "Update the epoch manager with the agreed median table",
          'TRANSITIONS': [
            {
              'NEXT_STATE': self.STATES.S0_WAIT_FOR_EPOCH_CHANGE,
              'TRANSITION_CONDITION': self.state_machine_api_callback_always_true,
              'ON_TRANSITION_CALLBACK': self.state_machine_api_callback_do_nothing,
              'DESCRIPTION': "Wait for the epoch to change to start a new sync process",
            }
          ],
        },
        self.STATES.S8_SEND_REQUEST_AGREED_MEDIAN_TABLE: {
          'STATE_CALLBACK': self.__receive_agreed_median_table_and_maybe_request_agreed_median_table,
          'DESCRIPTION': "Wait for the oracles to send the agreed median table and periodically request the agreed median table from the oracles",
          'TRANSITIONS': [
            {
              'NEXT_STATE': self.STATES.S9_COMPUTE_REQUESTED_AGREED_MEDIAN_TABLE,
              'TRANSITION_CONDITION': self.__send_request_agreed_median_table_timeout,
              'ON_TRANSITION_CALLBACK': self.state_machine_api_callback_do_nothing,
              'DESCRIPTION': "After the request phase time expires, compute the agreed median table from the received tables",
            },
            {
              'NEXT_STATE': self.STATES.S0_WAIT_FOR_EPOCH_CHANGE,
              'TRANSITION_CONDITION': self.__last_epoch_synced_is_previous_epoch,
              'ON_TRANSITION_CALLBACK': self.__reset_to_initial_state,
              'DESCRIPTION': "If the last epoch synced is the previous epoch, start a new sync process",
            }
          ],
        },
        self.STATES.S9_COMPUTE_REQUESTED_AGREED_MEDIAN_TABLE: {
          'STATE_CALLBACK': self.__compute_requested_agreed_median_table,
          'DESCRIPTION': "Compute the agreed median table of availability, based on the received tables",
          'TRANSITIONS': [
            {
              'NEXT_STATE': self.STATES.S0_WAIT_FOR_EPOCH_CHANGE,
              'TRANSITION_CONDITION': self.state_machine_api_callback_always_true,
              'ON_TRANSITION_CALLBACK': self.__reset_to_initial_state,
              'DESCRIPTION': "Begin the exchange process of the agreed median tables between oracles",
            }
          ],
        },
      }
      return job_state_transition_map

    def __reset_to_initial_state(self):
      """
      Reset the plugin to the initial state.
      """
      self.__current_epoch = self.netmon.epoch_manager.get_current_epoch()
      self.current_epoch_computed = False

      self.should_expect_to_participate = {}

      self.local_table = None
      self.dct_local_tables = {}
      self.first_time_local_table_sent = None
      self.last_time_local_table_sent = None

      self.median_table = None
      self.dct_median_tables = {}
      self.first_time_median_table_sent = None
      self.last_time_median_table_sent = None

      self.agreed_median_table = {}
      self.first_time_agreed_median_table_sent = None
      self.last_time_agreed_median_table_sent = None

      self.__last_epoch_synced = self.netmon.epoch_manager.get_last_sync_epoch()
      self.first_time_request_agreed_median_table_sent = None
      self.last_time_request_agreed_median_table_sent = None
      return

    # S0_WAIT_FOR_EPOCH_CHANGE
    def __send_epoch__agreed_median_table(self, start_epoch, end_epoch):
      dct_epoch__agreed_median_table = {}
      for epoch in range(start_epoch, end_epoch + 1):
        dct_epoch__agreed_median_table[epoch] = self.netmon.epoch_manager.get_epoch_availability(epoch)
      # end for

      self.add_payload_by_fields(
        epoch__agreed_median_table=dct_epoch__agreed_median_table,
      )
      return

    def __receive_requests_from_oracles_and_send_responses(self):
      """
      Receive requests from the oracles and send responses.
      """
      for dct_message in self.get_received_messages_from_oracles():
        sender = dct_message.get(self.ct.PAYLOAD_DATA.EE_SENDER)
        oracle_data = dct_message.get('ORACLE_DATA')
        stage = oracle_data.get('STAGE')
        request_agreed_median_table = oracle_data.get('REQUEST_AGREED_MEDIAN_TABLE')
        start_epoch = oracle_data.get('START_EPOCH')
        end_epoch = oracle_data.get('END_EPOCH')

        if stage != self.STATES.S8_SEND_REQUEST_AGREED_MEDIAN_TABLE:
          # received a message from a different stage
          continue

        if request_agreed_median_table:
          self.P(f"Received request from oracle {sender}: {stage = }, {start_epoch = }, {end_epoch = }")
          self.__send_epoch__agreed_median_table(start_epoch, end_epoch)
      # end for

      return

    def __epoch_finished(self):
      """
      Check if the epoch has changed.

      Returns
      -------
      bool : True if the epoch has changed, False otherwise
      """
      return self.__current_epoch != self.netmon.epoch_manager.get_current_epoch()

    # S1_COMPUTE_LOCAL_TABLE
    def __compute_local_table(self):
      """
      Compute the local table for the current node.
      If the node is not a supervisor, the local table will be empty.
      """
      # if current node is not supervisor, just return
      if not self.__is_supervisor(self.node_addr):
        self.P("I am not a supervisor. I will not participate in the sync process")
        self.local_table = {}
        return

      # node is supervisor, compute local table
      self.local_table = {
        node: self.netmon.epoch_manager.get_node_previous_epoch(node)
        for node in self.netmon.all_nodes
      }

      # if self is not full online, it should not participate in the sync process
      if not self.__was_full_online(self.node_addr):
        self.P("I was not full online. I will not participate in the sync process")
        return

      # if self is full online, it should participate in the sync process
      # mark oracles that were seen full online in the previous epoch as True
      for oracle in self.__get_oracle_list():
        self.should_expect_to_participate[oracle] = self.__was_potentially_full_online(oracle)

      self.P(f"Computed local table {self.local_table}")
      return

    def __can_participate_in_sync(self):
      """
      Check if the current node can participate in the sync process.
      A node can participate if it is a supervisor and was full online in the previous epoch.

      Returns
      -------
      bool : True if the node can participate in the sync process, False otherwise
      """
      return self.__is_supervisor(self.node_addr) and self.__was_full_online(self.node_addr)

    def __cannot_participate_in_sync(self):
      """
      Check if the current node cannot participate in the sync process.
      A node can participate if it is a supervisor and was full online in the previous epoch.

      Returns
      -------
      bool : True if the node cannot participate in the sync process, False otherwise
      """
      return not self.__can_participate_in_sync()

    # S2_SEND_LOCAL_TABLE
    def __receive_local_table_and_maybe_send_local_table(self):
      """
      Receive the local table from the oracles and 
      send the local table to the oracles each `self.cfg_send_interval` seconds.
      """
      # Receive values from oracles
      for dct_message in self.get_received_messages_from_oracles():
        sender = dct_message.get(self.ct.PAYLOAD_DATA.EE_SENDER)
        oracle_data = dct_message.get('ORACLE_DATA')
        stage = oracle_data.get('STAGE')
        local_table = oracle_data.get('LOCAL_TABLE')

        if not self.__check_received_local_table_ok(sender, oracle_data):
          continue

        self.P(f"Received message from oracle {sender}: {stage = }, {local_table = }")
        self.dct_local_tables[sender] = local_table
      # end for

      # Send value to oracles
      if self.first_time_local_table_sent is None:
        self.first_time_local_table_sent = self.time()

      if self.last_time_local_table_sent is not None and self.time() - self.last_time_local_table_sent < self.cfg_send_interval:
        return

      self.P(f"Sending {self.local_table=}")

      oracle_data = {
        'LOCAL_TABLE': self.local_table,
        'STAGE': self.__get_current_state()
      }
      self.bc.sign(oracle_data, add_data=True, use_digest=True)

      self.add_payload_by_fields(oracle_data=oracle_data)
      self.last_time_local_table_sent = self.time()
      return

    def __send_local_table_timeout(self):
      """
      Check if the exchange phase of the local table has finished.

      Returns
      -------
      bool: True if the exchange phase of the local table has finished, False otherwise
      """
      return self.time() - self.first_time_local_table_sent > self.cfg_send_period

    # S3_COMPUTE_MEDIAN_TABLE
    def __compute_median_table(self):
      """
      Compute the median table from the local tables received from the oracles.
      For each node that was seen in the local tables, compute the median value and sign it.
      """
      # should not have received any None values
      valid_local_tables = [x for x in self.dct_local_tables.values() if x is not None]
      valid_local_tables_count = len(valid_local_tables)

      if valid_local_tables_count <= self.__count_half_of_valid_oracles():
        self.median_table = None
        self.P("Could not compute median. Too few valid values", color='r')
        return

      # compute median for each node in list
      self.median_table = {}

      all_nodes_in_local_tables = set().union(*(set(value_table.keys()) for value_table in valid_local_tables))
      for node in all_nodes_in_local_tables:
        # default value 0 because if node not in value_table, it means it was not seen
        all_node_local_table_values = (value_table.get(node, 0) for value_table in valid_local_tables)
        valid_node_local_table_values = list(x for x in all_node_local_table_values if x is not None)

        # compute median and sign -- signature will be used in the next step
        self.median_table[node] = {'VALUE': round(self.np.median(valid_node_local_table_values))}
        self.bc.sign(self.median_table[node], add_data=True, use_digest=True)
# end for

      self.P(f"Computed median table {self.__compute_simple_median_table(self.median_table)}")
      return

    # S4_SEND_MEDIAN_TABLE
    def __receive_median_table_and_maybe_send_median_table(self):
      """
      Receive the median table from the oracles and
      send the median table to the oracles each `self.cfg_send_interval` seconds.
      """
      # Receive medians from oracles
      for dct_message in self.get_received_messages_from_oracles():
        sender = dct_message.get(self.ct.PAYLOAD_DATA.EE_SENDER)
        oracle_data = dct_message.get('ORACLE_DATA')
        stage = oracle_data.get('STAGE')
        median_table = oracle_data.get('MEDIAN_TABLE')

        if not self.__check_received_median_table_ok(sender, oracle_data):
          continue

        simple_median = self.__compute_simple_median_table(self.median_table)
        self.P(f"Received message from oracle {sender}: {stage = }, {simple_median = }")

        self.dct_median_tables[sender] = median_table
      # end for

      # Send median to oracles
      if self.first_time_median_table_sent is None:
        self.first_time_median_table_sent = self.time()

      if self.last_time_median_table_sent is not None and self.time() - self.last_time_median_table_sent < self.cfg_send_interval:
        return

      self.P(f"Sending median {self.__compute_simple_median_table(self.median_table)}")
      oracle_data = {
        'STAGE': self.__get_current_state(),
        'MEDIAN_TABLE': self.median_table,
      }
      self.bc.sign(oracle_data, add_data=True, use_digest=True)

      self.add_payload_by_fields(oracle_data=oracle_data)
      self.last_time_median_table_sent = self.time()
      return

    def __send_median_table_timeout(self):
      """
      Check if the exchange phase of the median table has finished.

      Returns
      -------
      bool: True if the exchange phase of the median table has finished, False otherwise
      """
      return self.time() - self.first_time_median_table_sent > self.cfg_send_period

    # S5_COMPUTE_AGREED_MEDIAN_TABLE
    def __compute_agreed_median_table(self):
      """
      Compute the agreed median table from the median tables received from the oracles.
      For each node that was seen in the median tables, compute the most frequent median value.
      """
      # im expecting all median tables to contain all nodes
      # but some errors can occur, so this does no harm
      all_nodes = set().union(*(set(value_table.keys()) for value_table in self.dct_median_tables.values()))

      # keep in a dictionary a list with all median values for each node
      dct_node_median_tables = {}
      for node in all_nodes:
        dct_node_median_tables[node] = [
          median_table[node]
          for median_table in self.dct_median_tables.values()
          if node in median_table
        ]
      # end for node

      # compute the frequency of each median value for each node
      for node in all_nodes:
        dct_median_frequentcy = {}
        for median in (dct_median['VALUE'] for dct_median in dct_node_median_tables[node]):
          if median not in dct_median_frequentcy:
            dct_median_frequentcy[median] = 0
          dct_median_frequentcy[median] += 1
        # end for median

        max_count = max(dct_median_frequentcy.values())
        most_frequent_median = next(k for k, v in dct_median_frequentcy.items() if v == max_count)

        # get all median table values that have the most frequent median
        # we do this because in the median table we find both the value and the signature
        lst_dct_freq_median = [
          dct_median
          for dct_median in dct_node_median_tables[node]
          if dct_median['VALUE'] == most_frequent_median
        ]

        if len(lst_dct_freq_median) > self.__count_half_of_valid_oracles():
          self.P(f"Computed agreed median table for node {node}: {most_frequent_median}. "
                 f"Dct freq {dct_median_frequentcy}")
          self.agreed_median_table[node] = {
            'VALUE': most_frequent_median,
            'SIGNATURES': lst_dct_freq_median,
          }
        else:
          self.P(f"Failed to compute agreed median table for node {node}. "
                 f"Could not achieve consensus. Dct freq:\n{self.json_dumps(dct_median_frequentcy, indent=2)}\n"
                 f"{self.json_dumps(self.dct_median_tables, indent=2)}", color='r')
          # this is a situation without recovery -- it can happen if the network is attacked
          # either the node is malicious or some oracles are malicious
          raise Exception("Failed to compute agreed median table")
          self.agreed_median_table[node] = {
            'VALUE': 0,
            'SIGNATURES': [],
          }
      # end for

      if len(self.agreed_median_table) == 0:
        self.P("Failed to compute agreed median table. Not enough online oracles", color='r')

      self.current_epoch_computed = True
      return

    # S6_SEND_AGREED_MEDIAN_TABLE
    def __receive_agreed_median_table_and_maybe_send_agreed_median_table(self):
      """
      Receive the agreed median table from the oracles and
      send the agreed median table to the oracles each `self.cfg_send_interval` seconds.
      """
      # Receive agreed values from oracles
      for dct_message in self.get_received_messages_from_oracles():
        sender = dct_message.get(self.ct.PAYLOAD_DATA.EE_SENDER)
        oracle_data = dct_message.get('ORACLE_DATA')
        stage = oracle_data.get('STAGE')
        agreed_median_table = oracle_data.get('AGREED_MEDIAN_TABLE')

        if not self.__check_received_agreed_median_table_ok(sender, oracle_data):
          continue

        simple_agreed_median_table = self.__compute_simple_agreed_value_table(agreed_median_table)
        self.P(f"Received message from oracle {sender}: {stage = }, {simple_agreed_median_table = }")
      # end for

      # Send agreed value to oracles
      if self.first_time_agreed_median_table_sent is None:
        self.first_time_agreed_median_table_sent = self.time()

      if self.last_time_agreed_median_table_sent is not None and self.time() - self.last_time_agreed_median_table_sent < self.cfg_send_interval:
        return

      oracle_data = {
          'STAGE': self.__get_current_state(),
          'AGREED_MEDIAN_TABLE': self.agreed_median_table,
        }

      self.P(f"Sending median table {self.__compute_simple_agreed_value_table(self.agreed_median_table)}")
      self.add_payload_by_fields(oracle_data=oracle_data)
      self.last_time_agreed_median_table_sent = self.time()
      return

    def __send_agreed_value_timeout(self):
      """
      Check if the exchange phase of the agreed median table has finished.

      Returns
      -------
      bool: True if the exchange phase of the agreed median table has finished, False otherwise
      """
      return self.time() - self.first_time_agreed_median_table_sent > self.cfg_send_period

    # S7_UPDATE_EPOCH_MANAGER
    def __update_epoch_manager_with_agreed_median_table(self, epoch=None, agreed_median_table=None):
      """
      Update the epoch manager with the agreed median table for the epoch.
      If both parameters are None, update the last epoch with `self.agreed_median_table`.

      Otherwise, update the target epoch with the agreed median table.

      Parameters
      ----------
      epoch : int, optional
          The epoch to update, by default None
      agreed_median_table : dict, optional
          The agreed median table to add to epoch manager history, by default None
      """

      if epoch is None:
        # update previous epoch
        epoch = self.netmon.epoch_manager.get_current_epoch() - 1
      # end if

      if agreed_median_table is None:
        agreed_median_table = self.agreed_median_table
      # end if

      if epoch <= self.__last_epoch_synced:
        self.P("Epoch manager history already updated with this epoch", color='r')
        return

      if epoch > self.__last_epoch_synced + 1:
        self.P(f"Detected a skip in epoch sync algorithm. "
               f"Last known epoch synced {self.__last_epoch_synced} "
               f"Current epoch {epoch}", color='r')
        return

      self.__last_epoch_synced = epoch

      self.netmon.epoch_manager.update_epoch_availability(epoch, agreed_median_table)
      return

    # S8_SEND_REQUEST_AGREED_MEDIAN_TABLE
    def __receive_agreed_median_table_and_maybe_request_agreed_median_table(self):
      """
      Receive the agreed median table from the oracles and
      request the agreed median table from the oracles each `self.cfg_send_interval` seconds.

      - if node receives the agreed median table for the last epoch, update the epoch manager
      - if node connects at 00:01, receives availability from 2 days ago, transition back to this state, then to s0
      - if node connects at 0X:00, receives availability from prev day, transition back to s0
      """

      # Receive agreed values from oracles
      for dct_message in self.get_received_messages_from_oracles():
        sender = dct_message.get(self.ct.PAYLOAD_DATA.EE_SENDER)
        oracle_data = dct_message.get('ORACLE_DATA')
        dct_epoch_agreed_median_table = oracle_data.get('EPOCH__AGREED_MEDIAN_TABLE')
        stage = oracle_data.get('STAGE')

        if stage != self.STATES.S0_WAIT_FOR_EPOCH_CHANGE:
          # received a message from a different stage
          continue

        if not self.__check_received_epoch__agreed_median_table_ok(sender, oracle_data):
          continue

        message_invalid = False
        for epoch, agreed_median_table in dct_epoch_agreed_median_table.items():
          if not self.__check_agreed_median_table(sender, agreed_median_table):
            # if one agreed median table is invalid, ignore the entire message
            message_invalid = True
            break
        # end for epoch agreed table

        if message_invalid:
          continue

        # sort dct_epoch_agreed_median_table by epoch in ascending order
        received_epochs = sorted(dct_epoch_agreed_median_table.keys())

        if self.__last_epoch_synced + 1 not in received_epochs or self.__current_epoch - 1 not in received_epochs:
          # Expected epochs in range [last_epoch_synced + 1, current_epoch - 1]
          # received epochs don t contain the full range
          continue

        self.P(f"Received availability table for epochs {received_epochs} from {sender = }. Keeping only the "
               f"tables for epochs in range [{self.__last_epoch_synced + 1}, {self.__current_epoch - 1}]")
        self.dct_median_tables[sender] = {i: dct_epoch_agreed_median_table[i]
                                          for i in range(self.__last_epoch_synced + 1, self.__current_epoch)}
      # end for received messages

      # Send request to get agreed value from oracles
      if self.first_time_request_agreed_median_table_sent is None:
        self.first_time_request_agreed_median_table_sent = self.time()

      if self.last_time_request_agreed_median_table_sent is not None and self.time() - self.last_time_request_agreed_median_table_sent < self.cfg_send_interval:
        return

      # Return if no need to sync; the last epoch synced is the previous epoch
      if self.__last_epoch_synced_is_previous_epoch():
        self.P("Last epoch synced is the previous epoch. No need to sync")
        return

      oracle_data = {
        'STAGE': self.__get_current_state(),
        'REQUEST_AGREED_MEDIAN_TABLE': True,
        'START_EPOCH': self.__last_epoch_synced + 1,
        'END_EPOCH': self.__current_epoch - 1,
      }

      self.P("Sending broadcast request for agreed median table for epochs "
             f"{self.__last_epoch_synced + 1} to {self.__current_epoch - 1}")
      self.add_payload_by_fields(oracle_data=oracle_data)
      self.last_time_request_agreed_median_table_sent = self.time()
      return

    def __send_request_agreed_median_table_timeout(self):
      """
      Check if the exchange phase of the agreed median table has finished.

      Returns
      -------
      bool: True if the exchange phase of the agreed median table has finished, False otherwise
      """
      # 10 times the normal period because we want to make sure that oracles can respond
      timeout_expired = self.time() - self.first_time_request_agreed_median_table_sent > self.cfg_send_period * 10

      return not self.__last_epoch_synced_is_previous_epoch() and timeout_expired

    def __last_epoch_synced_is_previous_epoch(self):
      """
      Check if the agreed median table for the last epoch has been received.

      Returns
      -------
      bool: True if the agreed median table for the last epoch has been received, False otherwise
      """
      return self.__last_epoch_synced == self.__current_epoch - 1

    # S9_COMPUTE_REQUESTED_AGREED_MEDIAN_TABLE
    def __compute_requested_agreed_median_table(self):
      """
      Compute the agreed median table from the received tables.
      """

      """
      self.dct_median_tables = {
        'oracle1': {
          epoch1: {
            node1: {VALUE: 1, SIGNATURE: 'signature'},
            node2: {VALUE: 2, SIGNATURE: 'signature'},
          },
          epoch2: {
            node1: {VALUE: 1, SIGNATURE: 'signature'},
            node2: {VALUE: 2, SIGNATURE: 'signature'},
          },
        },
        'oracle2': {
          epoch1: {
            node1: {VALUE: 1, SIGNATURE: 'signature'},
            node2: {VALUE: 2, SIGNATURE: 'signature'},
          },
          epoch2: {
            node1: {VALUE: 1, SIGNATURE: 'signature'},
            node2: {VALUE: 2, SIGNATURE: 'signature'},
          },
        },
      }
      """
      # self.dct_median_tables contains dict with epoch as key and agreed median table as value

      dct_epoch_lst_agreed_median_table = {}
      for _, dct_epoch_agreed_median_table in self.dct_median_tables.items():
        for epoch, agreed_median_table in dct_epoch_agreed_median_table.items():
          if epoch not in dct_epoch_lst_agreed_median_table:
            dct_epoch_lst_agreed_median_table[epoch] = []
          dct_epoch_lst_agreed_median_table[epoch].append(agreed_median_table)
        # end for epoch agreed table
      # end for received messages

      # we make sure the epochs are in ascending order
      epochs_in_order = sorted(dct_epoch_lst_agreed_median_table.keys())
      for epoch in epochs_in_order:
        if epoch <= self.__last_epoch_synced:
          self.P(f"Epoch {epoch} already synced "
                 f"(last_epoch_synced= {self.__last_epoch_synced}). Skipping", color='r')
          # we already have the agreed median table for this epoch
          continue
        lst_agreed_median_table = dct_epoch_lst_agreed_median_table[epoch]
        # im expecting all median tables to contain all nodes
        # but some errors can occur, so this does no harm
        all_nodes = set().union(*(set(value_table.keys()) for value_table in lst_agreed_median_table))

        # keep in a dictionary a list with all median values for each node
        dct_node_median_tables = {}
        for node in all_nodes:
          dct_node_median_tables[node] = [
            median_table[node]
            for median_table in lst_agreed_median_table
            if node in median_table
          ]
        # end for node

        # compute the frequency of each median value for each node
        epoch__agreed_median_table = {}

        for node in all_nodes:
          dct_median_frequentcy = {}
          for median in (dct_median['VALUE'] for dct_median in dct_node_median_tables[node]):
            if median not in dct_median_frequentcy:
              dct_median_frequentcy[median] = 0
            dct_median_frequentcy[median] += 1
          # end for median

          max_count = max(dct_median_frequentcy.values())
          most_frequent_median = next(k for k, v in dct_median_frequentcy.items() if v == max_count)

          # get all median table values that have the most frequent median
          # we do this because in the median table we find both the value and the signature
          lst_dct_freq_median = [
            dct_median
            for dct_median in dct_node_median_tables[node]
            if dct_median['VALUE'] == most_frequent_median
          ]

          epoch__agreed_median_table[node] = lst_dct_freq_median[0]
        # end for node
        simple_epoch__agreed_median_table = self.__compute_simple_agreed_value_table(epoch__agreed_median_table)
        self.P(f"Computed availability table for {epoch = }, {simple_epoch__agreed_median_table = }")
        self.__update_epoch_manager_with_agreed_median_table(epoch, epoch__agreed_median_table)
      # end for epoch
      return

  # Utils
  if True:
    def __is_supervisor(self, node: str):
      """
      Check if the node is a supervisor.

      Parameters
      ----------
      node : str
          The node to check

      Returns
      -------
      bool : True if the node is a supervisor, False otherwise
      """
      return self.netmon.network_node_is_supervisor(node)

    def __was_full_online(self, node: str):
      """
      Check if the node was full online in the previous epoch.

      Parameters
      ----------
      node : str
          The node to check

      Returns
      -------
      bool : True if the node was full online in the previous epoch, False otherwise
      """
      return self.local_table.get(node, 0) == 255

    def __was_potentially_full_online(self, node: str):
      """
      Check if the node was potentially full online in the previous epoch.
      Potentially full online means that the node was seen with a value of 254 or 255.
      We accept 254 because the current node and the target node could have been
      offline for < 2 min in different intervals, which means that neither of them
      received heartbeats from the other for a period of 4 minutes.

      Parameters
      ----------
      node : str
          The node to check

      Returns
      -------
      bool : True if the node was potentially full online in the previous epoch, False otherwise
      """
      return self.local_table.get(node, 0) >= 254

    def __get_oracle_list(self):
      """
      Get the list of oracles.
      For now we consider that all supervisors are oracles.

      Returns
      -------
      list : The list of oracles
      """
      return [node for node in self.netmon.all_nodes if self.__is_supervisor(node)]

    def __get_current_state(self):
      """
      Get the current state of the state machine.

      Returns
      -------
      str : The current state of the state machine
      """
      return self.state_machine_api_get_current_state(self.state_machine_name)

    def __count_half_of_valid_oracles(self):
      """
      Count the number of oracles that are expected to participate in the sync process.

      Returns
      -------
      int : The number of oracles that are expected to participate in the sync process
      """
      return sum(self.should_expect_to_participate.values()) / 2

    def get_received_messages_from_oracles(self):
      """
      Get the messages received from the oracles.
      This method returns a generator for memory efficiency.

      Returns
      -------
      generator : The messages received from the oracles
      """
      dct_messages = self.dataapi_struct_datas()
      received_messages = (dct_messages[i] for i in range(len(dct_messages)))

      # we use a DCT that already filters the messages from the oracles
      received_messages_from_oracles = received_messages
      return received_messages_from_oracles

    def __check_received_local_table_ok(self, sender, oracle_data):
      """
      Check if the received value table is ok. Print the error message if not.

      Parameters:
      ----------
      sender : str
        The sender of the message
      oracle_data : dict
        The data received from the oracle

      Returns:
      -------
      bool : True if the received value table is ok, False otherwise
      """
      sentinel = object()

      stage = oracle_data.get('STAGE', sentinel)
      signature = oracle_data.get('EE_SIGN', sentinel)
      value = oracle_data.get('VALUE', sentinel)

      if stage == sentinel or signature == sentinel or value == sentinel:
        self.P(f"Received message from oracle {sender} with missing fields: "
               f"{sentinel = }, {stage = }, {signature = }, {value = }", color='r')
        return False

      if stage is None or signature is None:
        self.P(f"Received message from oracle {sender} with `None` fields: "
               f"{stage = }, {signature = }", color='r')
        return False

      if stage != self.STATES.S2_SEND_LOCAL_TABLE:
        self.P(f"Received message from oracle {sender} with wrong stage: {stage = }", color='r')
        return False

      if not self.bc.verify(dct_data=oracle_data, str_signature=None, sender_address=None)['valid']:
        self.P(f"Invalid signature from oracle {sender}", color='r')
        return False

      if not self.should_expect_to_participate.get(sender, False) and value is not None:
        self.P(f"Node {sender} should not have sent value {value}. ignoring...", color='r')
        return False

      if self.should_expect_to_participate.get(sender, False) and value is None:
        self.P(f"Oracle {sender} should have sent value. ignoring...", color='r')
        return False

      return True

    def __check_received_median_table_ok(self, sender, oracle_data):
      """
      Check if the received median is ok. Print the error message if not.

      Parameters:
      ----------
      sender : str
        The sender of the message
      oracle_data : dict
        The data received from the oracle

      Returns:
      -------
      bool : True if the received median is ok, False otherwise
      """

      sentinel = object()

      stage = oracle_data.get('STAGE', sentinel)
      signature = oracle_data.get('EE_SIGN', sentinel)
      median = oracle_data.get('MEDIAN', sentinel)

      if stage == sentinel or signature == sentinel or median == sentinel:
        self.P(f"Received message from oracle {sender} with missing fields: "
               f"{sentinel = }, {stage = }, {signature = }, {median = }", color='r')
        return False

      if stage is None or signature is None:
        self.P(f"Received message from oracle {sender} with `None` fields: "
               f"{stage = }, {signature = }", color='r')
        return False

      if stage != self.STATES.S4_SEND_MEDIAN_TABLE:
        self.P(f"Received message from oracle {sender} with wrong stage: {stage = }", color='r')
        return False

      if not self.bc.verify(dct_data=oracle_data, str_signature=None, sender_address=None)['valid']:
        self.P(f"Invalid signature from oracle {sender}", color='r')
        return False

      # in the should expect to participate dictionary, only oracles that were seen
      # as full online are marked as True
      if not self.should_expect_to_participate.get(sender, False) and median is not None:
        self.P(f"Oracle {sender} should not have sent median {median}. ignoring...", color='r')
        return False

      if median is None:
        self.P(f"Oracle {sender} could not compute median. ignoring...", color='r')
        return False

      return True

    def __check_received_agreed_median_table_ok(self, sender, oracle_data):
      """
      Check if the received agreed value is ok. Print the error message if not.

      Parameters:
      ----------
      sender : str
        The sender of the message
      oracle_data : dict
        The data received from the oracle

      Returns:
      -------
      bool : True if the received agreed value is ok, False otherwise
      """
      sentinel = object()

      stage = oracle_data.get('STAGE', sentinel)
      agreed_median_table = oracle_data.get('AGREED_MEDIAN_TABLE', sentinel)

      if stage == sentinel or agreed_median_table == sentinel:
        self.P(f"Received message from oracle {sender} with missing fields: "
               f"{sentinel = }, {stage = }, {agreed_median_table = }", color='r')
        return False

      if stage is None or agreed_median_table is None:
        self.P(f"Received message from oracle {sender} with `None` fields: "
               f"{stage = }, {agreed_median_table = }", color='r')
        return False

      if stage != self.STATES.S6_SEND_AGREED_MEDIAN_TABLE:
        self.P(f"Received message from oracle {sender} with wrong stage: {stage = }", color='r')
        return False

      # in the should expect to participate dictionary, only oracles that were seen
      # as full online are marked as True
      if not self.should_expect_to_participate.get(sender, False) and agreed_median_table is not None:
        self.P(f"Oracle {sender} should not have sent agreed_value_table {agreed_median_table}. ignoring...", color='r')
        return False

      if not self.__check_agreed_median_table(sender, agreed_median_table):
        return False

      values_signed_ok = all(
        dct_node['VALUE'] == self.agreed_median_table[node]['VALUE']
        for node, dct_node in agreed_median_table.items()
      )
      if not values_signed_ok:
        self.P(f"Invalid agreed value from oracle {sender}", color='r')
        return False

      return True

    def __check_received_epoch__agreed_median_table_ok(self, sender, oracle_data):
      """
      Check if the received agreed value is ok. Print the error message if not.
      This method is used to check if the message received is valid. The checking
      of each agreed median table is done in the __check_agreed_median_table method.

      Parameters
      ----------
      sender : str
          The sender of the message
      oracle_data : dict
          The data received from the oracle
      """
      sentinel = object()

      epoch__agreed_median_table = oracle_data.get('EPOCH__AGREED_MEDIAN_TABLE', sentinel)

      if epoch__agreed_median_table == sentinel:
        self.P(f"Received message from oracle {sender} with missing fields: "
               f"{sentinel = }, {epoch__agreed_median_table = }", color='r')
        return False

      if epoch__agreed_median_table is None:
        self.P(f"Received message from oracle {sender} with `None` fields: "
               f"{epoch__agreed_median_table = }", color='r')
        return False

      return True

    def __check_agreed_median_table(self, sender, agreed_median_table):
      """
      Check if the agreed median table is valid.

      Parameters
      ----------
      sender : str
          The sender of the message
      agreed_median_table : dict
          The agreed median table received from the oracle
      """

      if agreed_median_table is None:
        self.P(f"Received agreed median table from oracle {sender} is None. ignoring...", color='r')
        return False

      median_signatures_ok = all(
        all(
          self.bc.verify(dct_data=signature, str_signature=None, sender_address=None)['valid']
          for signature in dct_node['SIGNATURES']
        )
        for dct_node in agreed_median_table.values()
      )
      if not median_signatures_ok:
        self.P(f"Invalid signatures from oracle {sender}", color='r')
        return False

      values_same = all(
        all(dct_node['VALUE'] == signature['VALUE'] for signature in dct_node['SIGNATURES'])
        for dct_node in agreed_median_table.values()
      )
      if not values_same:
        self.P(f"Signatures from oracle {sender} are for values different than the agreed value", color='r')
        return False

      return True

    def __compute_simple_median_table(self, median_table):
      """
      Compute a simple median table with only the values.
      This method is used to print the median table in a more readable format.

      Parameters
      ----------
      median_table : dict
          The median table to simplify

      Returns
      -------
      dict : The simplified median table
      """
      if median_table is None:
        return None
      simple_median_table = {}
      for node, dct_node in median_table.items():
        simple_median_table[node] = dct_node['VALUE']

      return simple_median_table

    def __compute_simple_agreed_value_table(self, agreed_value_table):
      """
      Compute a simple agreed value table with only the values.
      This method is used to print the agreed value table in a more readable format.

      Parameters
      ----------
      agreed_value_table : dict
          The agreed value table to simplify

      Returns
      -------
      dict : The simplified agreed value table
      """
      if agreed_value_table is None:
        return None
      simple_agreed_value_table = {}
      for node, dct_node in agreed_value_table.items():
        simple_agreed_value_table[node] = dct_node['VALUE']

      return simple_agreed_value_table

  def on_command(self, data, request_agreed_median_table=None, **kwargs):
    # should receive command to send the agreed median table for a set of epochs
    # this is useful for a new oracle that connects to the network and needs to catch up
    # used in state S7_WAIT_FOR_ORACLE_SYNC

    # WARNING! using the new api for commands
    if request_agreed_median_table:
      start_epoch = data.get("START_EPOCH", None)
      end_epoch = data.get("END_EPOCH", None)
      if start_epoch is None or end_epoch is None:
        self.P(f"Received command without start or end epochs defined. "
               f"Interval [{start_epoch}, {end_epoch}]. Ignoring...", color='r')
        return

      dct_epoch__agreed_median_table = {}
      for epoch in range(start_epoch, end_epoch + 1):
        dct_epoch__agreed_median_table[epoch] = self.netmon.epoch_manager.get_epoch_availability(epoch)
      # end for

      self.P(f"Received request to send agreed median table for closed epoch interval [{start_epoch}, {end_epoch}]")
      self.add_payload_by_fields(
        epoch__agreed_median_table=dct_epoch__agreed_median_table,
        command_params=data,
      )
    return

  def process(self):
    self.state_machine_api_step(self.state_machine_name)
    return

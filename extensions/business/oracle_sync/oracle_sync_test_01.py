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
"""

from extensions.business.oracle_sync.oracle_sync_01 import OracleSync01Plugin as BaseClass

_CONFIG = {
  **BaseClass.CONFIG,

  "DUMMY_SENDER": None,
  'LAST_EPOCH_SYNCED': 0,

  'VALIDATION_RULES': {
    **BaseClass.CONFIG['VALIDATION_RULES'],
  },
}

__VER__ = '0.1.0'


class OracleSyncTest01Plugin(BaseClass):

  def _OracleSync01Plugin__reset_to_initial_state(self):
    """
    Reset the plugin to the initial state.
    """
    self._OracleSync01Plugin__current_epoch = self.netmon.epoch_manager.get_current_epoch() # TODO
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

    self._OracleSync01Plugin__last_epoch_synced = self.cfg_last_epoch_synced
    self.first_time_request_agreed_median_table_sent = None
    self.last_time_request_agreed_median_table_sent = None
    return

  # State machine callbacks
  if True:
    # S0_WAIT_FOR_EPOCH_CHANGE
    def _OracleSync01Plugin__epoch_finished(self):
      """
      Check if the epoch has changed.

      Returns
      -------
      bool : True if the epoch has changed, False otherwise
      """
      return self.__current_epoch != self.netmon.epoch_manager.get_current_epoch() # TODO

    # S1_COMPUTE_LOCAL_TABLE
    def _OracleSync01Plugin__compute_local_table(self):
      """
      Compute the local table for the current node.
      If the node is not a supervisor, the local table will be empty.
      """
      self.oracle_list = ['sender0', 'sender1', 'sender2']
      # self.oracle_list = ['sender0']
      self.value_table = {
        'sender0': self.np.random.randint(255, 256),
        'sender1': self.np.random.randint(255, 256),
        'sender2': self.np.random.randint(100, 102),
        'a': self.np.random.randint(100 - 1, 100 + 2),
      }
      self.P(f"Computed value table {self.value_table}")

      # if self.cfg_sender_dummy == 'sender2' or self.cfg_sender_dummy == 'sender1':
      #   self.P(f"I, {self.cfg_sender_dummy}, am a bandit. I will try to break the consensus")
      #   self.value_table = {
      #     'sender0': 0,
      #     'sender1': 255,
      #     'sender2': 255,
      #     'a': 0,
      #   }

      for oracle in self.__get_oracle_list():
        self.should_expect_to_participate[oracle] = self._OracleSync01Plugin__was_potentially_full_online(oracle)

      return


    def _OracleSync01Plugin__can_participate_in_sync(self):
      """
      Check if the current node can participate in the sync process.
      A node can participate if it is a supervisor and was full online in the previous epoch.

      Returns
      -------
      bool : True if the node can participate in the sync process, False otherwise
      """
      return self.__is_supervisor(self.cfg_dummy_sender) and self.__was_full_online(self.cfg_dummy_sender)

  # Utils
  if True:
    def _OracleSync01Plugin__is_supervisor(self, node: str):
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
      return node in self.__get_oracle_list()

    def _OracleSync01Plugin__get_oracle_list(self):
      """
      Get the list of oracles.
      For now we consider that all supervisors are oracles.

      Returns
      -------
      list : The list of oracles
      """
      return ['sender0', 'sender1', 'sender2']

    def get_received_messages_from_oracles(self):
      """
      Get the messages received from the oracles.
      This method returns a generator for memory efficiency.

      Returns
      -------
      generator : The messages received from the oracles
      """
      dct_messages = self.dataapi_struct_datas()
      received_messages = [dct_messages[i] for i in range(len(dct_messages))]
      
      for message in received_messages:
        message[self.ct.PAYLOAD_DATA.EE_SENDER] = message['DUMMY_SENDER']

      # we use a DCT that already filters the messages from the oracles
      received_messages_from_oracles = received_messages
      return received_messages_from_oracles

    def add_payload_by_fields(self, **kwargs):
      """
      Add the payload to the message by fields.

      Parameters
      ----------
      **kwargs : dict
          The fields to add to the payload
      """
      super(OracleSyncTest01Plugin, self).add_payload_by_fields(dummy_sender=self.cfg_dummy_sender, **kwargs)
      return

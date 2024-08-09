from extensions.business.chain_dist.process_real_time_collected_data_chain_dist import ProcessRealTimeCollectedDataChainDistPlugin

_CONFIG = {
  **ProcessRealTimeCollectedDataChainDistPlugin.CONFIG,


  # Worker specific config
  'NODE_DEFAULT_INSTANCE_ID': "Default",
  'NODE_SIGNATURE': 'CUSTOM_EXEC_01',

  'NODE_PIPELINE_CONFIG': {
    'reconnectable': "keepalive",
    "cap_resolution": 15,
    "live": False,
    "live_feed": False,
    'stream_type': 'VideoFile',
  },
  ##########################

  # Master specific config
  'CANCEL_ALL_JOBS_ON_EXCEPTION': False,
  'NO_NODES': 5,  # is a number
  'NODES': None,  # can be list
  'NODE_TIMEOUT': 2.5 * 60,  # seconds

  'PING_SEND_PERIOD_MIN': 2,  # seconds
  'PING_SEND_PERIOD_MAX': 10,  # seconds

  ##########################
  # Plugin specific config
  'CUSTOM_CODE_PROCESS_REAL_TIME_COLLECTED_DATA': None,
  'CUSTOM_CODE_FINISH_CONDITION': None,
  "CUSTOM_CODE_AGGREGATE_COLLECTED_DATA": None,

  "CUSTOM_CODE_REMOTE_NODE": None,

  "NODE_PLUGIN_CONFIG": {},
  ##########################

  "VALIDATION_RULES": {
    **ProcessRealTimeCollectedDataChainDistPlugin.CONFIG["VALIDATION_RULES"],
  },
}


class ProcessRealTimeCollectedDataCustomExecChainDistPlugin(ProcessRealTimeCollectedDataChainDistPlugin):
  def on_init(self):
    pass

  def __handle_errors_and_warnings(self, errors, warnings):
    if errors is not None:
      raise Exception("The custom code failed with the following error: {}".format(errors))
      
    if len(warnings) > 0:
      self.P("The custom code generated the following warnings: {}".format("\n".join(warnings)))
    return

  # Distribution Logic
  def split_input(self):
    """
    This method must split the input data into shards and store them in the `self.input_shards` list.
    This method can take as long as it needs
    It is recommended that `self.input_shards` is populated at the end of this method.
    """
    
    return [None] * self.nr_remote_nodes

  def __custom_code_aggregate_collected_data(self, collected_data):
    custom_code_method, errors, warnings = self._get_method_from_custom_code(
      str_b64code=self.cfg_custom_code_aggregate_collected_data,
      self_var='plugin',
      method_arguments=['plugin', 'collected_data']
    )
    self.__handle_errors_and_warnings(errors, warnings)

    return custom_code_method(self, collected_data)

  def aggregate_collected_data(self, collected_data):
    # TODO: change from node data to collected data
    """
    Merge the output of the nodes. This method must call the `self.create_golden_payload` method.

    Parameters
    ----------
    collected_data : list
        List of data from the nodes. The list elements are in the order expected order.
    """
    merged_data = self.__custom_code_aggregate_collected_data(collected_data)
    self.create_golden_payload(data=merged_data)

    return

  def generate_node_plugin_configuration(self, input_shard, node_id):
    config_plugin = {
      "SIGNATURE": self.cfg_node_signature,
      "INSTANCES": [{
        "INSTANCE_ID": self.cfg_node_default_instance_id,
        "CODE": self.cfg_custom_code_remote_node,
        "RESULT_KEY": "DATA",
        "PROCESS_DELAY": 0.01,
        **self.cfg_node_plugin_config
      }]
    }

    return config_plugin

  def __custom_code_process_real_time_collected_data(self, job_id, collected_data, data):
    custom_code_method, errors, warnings = self._get_method_from_custom_code(
      str_b64code=self.cfg_custom_code_process_real_time_collected_data,
      self_var='plugin',
      method_arguments=['plugin', 'job_id', 'collected_data', 'data']
    )
    self.__handle_errors_and_warnings(errors, warnings)

    return custom_code_method(self, job_id, collected_data, data)

  def process_real_time_collected_data(self, job_id, collected_data, data):
    """
    Process the real time data from the node.

    Parameters
    ----------
    job_id: int
        The index of the job.
    collected_data : dict
        The data collected from all the nodes up to this point.
    data : Any
        The data from the node.

    Returns
    -------
    processed_data : Any | None
        The processed data. If None, the data is ignored.
    """
    
    return self.__custom_code_process_real_time_collected_data(job_id, collected_data, data)

  def __custom_code_finish_condition(self, collected_data):
    custom_code_method, errors, warnings = self._get_method_from_custom_code(
      str_b64code=self.cfg_custom_code_finish_condition,
      self_var='plugin',
      method_arguments=['plugin', 'collected_data']
    )
    self.__handle_errors_and_warnings(errors, warnings)

    return custom_code_method(self, collected_data)

  def finish_condition(self, collected_data):
    """
    This method must return True if all the nodes finished their jobs.
    This method is called if `PROCESS_REAL_TIME_NODE_DATA` is True, as the nodes will send data in real time.

    Parameters
    ----------
    collected_data : dict
        All the data collected from the nodes. 
        This is a list of data shards returned by `self.process_real_time_collected_data` method, in the format defined by the user. 
    """
    return self.__custom_code_finish_condition(collected_data)
  
  def custom_status_payload(self):
    """
    This method must return a custom status payload.
    """
    aggregated_data = self.__custom_code_aggregate_collected_data(self._collected_data)

    return {
      "DATA": aggregated_data
    }

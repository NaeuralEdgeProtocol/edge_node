from abc import abstractclassmethod

from extensions.business.chain_dist.base_chain_dist import BaseChainDistPlugin as BaseClass

_CONFIG = {
  **BaseClass.CONFIG,

  # Developer config
  'MAX_INPUTS_QUEUE_SIZE': 500,
  'ALLOW_EMPTY_INPUTS': True,
  'DEFAULT_NO_NODES': 4,
  ##########################

  # Worker specific config
  'NODE_DEFAULT_INSTANCE_ID': "Default",
  'NODE_SIGNATURE': 'SMART_CHAIN_DIST_DUMMY_RANDOM',

  'NODE_PIPELINE_CONFIG': {
    'reconnectable': 'KEEPALIVE',
    'live_feed': False,
    'cap_resolution': 10,
    'stream_type': 'a_dummy_dataframe',
  },
  ##########################

  # Master specific config
  'CANCEL_ALL_JOBS_ON_EXCEPTION': False,
  'NO_NODES': None,  # is a number
  'NODES': None,  # can be list
  'NODE_TIMEOUT': 2.5 * 60,  # seconds

  'PING_SEND_PERIOD_MIN': 30,  # seconds
  'PING_SEND_PERIOD_MAX': 60,  # seconds
  ##########################

  'VALIDATION_RULES': {
    **BaseClass.CONFIG['VALIDATION_RULES'],
  },
}


class ProcessRealTimeCollectedDataChainDistPlugin(BaseClass):
  CONFIG = _CONFIG

  # Job lifecycle callbacks
  def _job_on_data_callback(self, job_id, pipeline, payload):
    payload = dict(payload)
    job = self._jobs[job_id]
    job.last_payload_time = self.time()
    
    job.progress = payload.get('PROGRESS', 0)
    data = payload.get('DATA', None) or payload.get('RESOURCE', None)
    
    # if no useful payload, return
    if data is None:
      return

    # real time processing
    job.unprocessed_data.append(data)

    return

  def _job_in_progress_and_healthy(self, job_id):
    job = self._jobs[job_id]

    last_payload_was_too_long_ago = self.time() - job.last_payload_time > self.cfg_node_timeout
    job_is_healthy = job.failed is False

    if last_payload_was_too_long_ago:
      job.failed = True

    # if we process the data in real time, we do not care about the progress
    master_job_finished = self.finish_condition(self._collected_data)
    return not last_payload_was_too_long_ago and job_is_healthy and not master_job_finished

  def _maybe_save_job_results(self, job_id):
    job = self._jobs[job_id]
    # if job.get('failed', False) is False:
    #   self._dct_finished_jobs[job_id] = True

    return

  # Job lifecycle management
  def _step_state_all_jobs(self):
    for job_id in self._jobs:
      job = self._jobs[job_id]
      self.state_machine_api_step(name=job.job_name)
    return

  def _handle_unprocessed_data(self):
    for job_id in self._jobs:
      job = self._jobs[job_id]
      if job.get('failed', False) is False:
        no_unprocessed_data = len(job.unprocessed_data)
        for _ in range(no_unprocessed_data):
          data = job.unprocessed_data.pop(0)
          processed_data = self.process_real_time_collected_data(job_id, self._collected_data, data)

          # if the data is not useful, return
          if processed_data is None:
            continue

          if isinstance(processed_data, list):
            for pd in processed_data:
              self._collected_data[job_id].append(pd)
          else:
            self._collected_data[job_id].append(processed_data)
    return

  def _distribute_jobs(self):
    super(ProcessRealTimeCollectedDataChainDistPlugin, self)._distribute_jobs()
    self._handle_unprocessed_data()

    if self._finish_condition():
      # TODO: this might not work as expected, please fix
      self._step_state_all_jobs()

    return

  # Master state machine
  @property
  def _progress_by_node(self):
    nodes = [v.get('node') for v in self._jobs.values()]
    count_collected_data_per_node = [len(self._collected_data[job_id]) for job_id in self._jobs]
    if sum(count_collected_data_per_node) == 0:
      return {}
    prc_collected_data_per_node = [cnt / sum(count_collected_data_per_node) for cnt in count_collected_data_per_node]

    progress_by_node = {k: {'NODE': node, 'PROGRESS': prc} for k, node, prc in zip(self._jobs.keys(), nodes, prc_collected_data_per_node)}
    return progress_by_node

  def _finish_condition(self):
    return self.finish_condition(self._collected_data)

  def _aggregate_collected_data_and_compute_golden_payload(self):
    self._aggregate_collected_data(self._collected_data)
    return

  # Customizable Logic
  @abstractclassmethod
  def process_real_time_collected_data(self, job_id, collected_data, data):
    """
    Process the real time data from the node.

    Parameters
    ----------
    job_id : int
        The index of the job.
    collected_data : dict
        The data collected from all the nodes up to this point.
    data : Any
        The data from the node.

    Returns
    -------
    processed_data : dict | None
        The processed data. If None, the data is ignored.
    """
    raise NotImplementedError

  @abstractclassmethod
  def finish_condition(self, collected_data):
    """
    This method must return True if all the nodes finished their jobs.

    Parameters
    ----------
    collected_data : dict
        All the data collected from the nodes. 
        This is a list of data shards returned by `self.process_real_time_collected_data` method, in the format defined by the user. 
    """
    raise NotImplementedError

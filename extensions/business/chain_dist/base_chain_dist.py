from abc import abstractclassmethod
import threading
from functools import partial
from PyE2 import Session, Pipeline, Instance

from core.business.base import BasePluginExecutor as BaseClass
from extensions.business.mixins.chain_dist_merge_mixin import _ChainDistMergeMixin
from extensions.business.mixins.chain_dist_split_mixin import _ChainDistSplitMixin

_CONFIG = {
  **BaseClass.CONFIG,

  # Developer config
  'MAX_INPUTS_QUEUE_SIZE': 500,
  'ALLOW_EMPTY_INPUTS': True,
  'DEFAULT_NR_REMOTE_NODES': 4,
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
  'NR_REMOTE_NODES': None,  # is a number
  'NODES': None,  # can be list
  'NODE_TIMEOUT': 2.5 * 60,  # seconds

  'PING_SEND_PERIOD_MIN': 30,  # seconds
  'PING_SEND_PERIOD_MAX': 60,  # seconds
  ##########################

  'VALIDATION_RULES': {
    **BaseClass.CONFIG['VALIDATION_RULES'],
  },
}


class BaseChainDistPlugin(BaseClass, _ChainDistSplitMixin, _ChainDistMergeMixin):
  CONFIG = _CONFIG

  class STATE:
    S1_DECIDE_NR_REMOTE_NODES = 'S1_DECIDE_NR_REMOTE_NODES'
    S2_SPLIT_INPUT = 'SPLIT_INPUT'
    S3_DISTRIBUTE_JOBS = 'DISTRIBUTE_JOBS'
    S4_AGGREGATE_COLLECTED_DATA = 'AGGREGATE_COLLECTED_DATA'
    S5_FINISHED = 'FINISHED'

  class SUB_STATE:
    CHOOSE_NODE = 'CHOOSE_NODE'
    WAITING_START_CONFIMATION = 'WAITING_START_CONFIMATION'
    JOB_PROGRESS = 'JOB_PROGRESS'
    WAITING_CLOSING_CONFIRMATION = 'WAITING_CLOSING_CONFIRMATION'
    CLOSED_JOB = 'CLOSED_JOB'

  def startup(self):
    super().startup()
    
    self._session = Session(
      name=f'{self.str_unique_identification}',
      config=self.global_shmem['config_communication']['PARAMS'],
      log=self.log,
      bc_engine=self.global_shmem[self.ct.BLOCKCHAIN_MANAGER],
    )

    self.__state_machine_name = "Chain Dist"
    self.state_machine_api_init(
      name=self.__state_machine_name, 
      state_machine_transitions=self._prepare_main_state_machine_transitions(), 
      initial_state=self.STATE.S1_DECIDE_NR_REMOTE_NODES, 
      on_successful_step_callback=self.__save_state
    )

    self.__split_input_thread = None
    self.input_shards = []

    self.__aggregate_collected_data_thread = None

    self._dct_finished_jobs = {}

    self._nr_remote_nodes = None
    self._jobs = self.NestedDotDict()
    self._collected_data = {}
    self._golden_payload = None
    self._golden_payload_kwargs = None

    self.__critical_failure = False

    self._last_time_ping_send = 0
    self._last_sent_progress = 0

    self._unused_configured_nodes = []

    self.dct_persistent_data = {}

    self.dct_state_timestamps = {}

    if self.cfg_nodes is not None:
      self._unused_configured_nodes = [node for node in self.cfg_nodes]

    self.__load_state()
    self.__last_time_saved_state = 0

    return

  # Persistence methods
  def __save_state(self, lazy=False):

    if lazy:
      if self.time() - self.__last_time_saved_state < 5:
        return

    self.__last_time_saved_state = self.time()
    jobs = {}

    for job_id, job in self._jobs.items():
      jobs[job_id] = dict(job)
      if job.in_progress:
        jobs[job_id]["state_machine_current_state"] = self._get_job_state_machine_state(job_id)

    dct_current_state = {
      'dct_finished_jobs': self._dct_finished_jobs,
      'nr_remote_nodes': self._nr_remote_nodes,
      'jobs': jobs,
      'collected_data': self._collected_data,
      'golden_payload_kwargs': self._golden_payload_kwargs,
      'input_shards': self.input_shards,
      'critical_failure': self.__critical_failure,
      'unused_configured_nodes': self._unused_configured_nodes,
      'chain_dist_state': self.__get_chain_dist_state(),
      'persistent_data': self.dct_persistent_data,
    }

    self.persistence_serialization_save(dct_current_state)
    return

  def __delete_state(self):
    # TODO: implement
    return

  def __load_state(self):
    # read from local cache the last known state of this instance
    dct_last_state = self.persistence_serialization_load()

    if dct_last_state is not None:
      self._dct_finished_jobs = dct_last_state['dct_finished_jobs']
      self._nr_remote_nodes = dct_last_state['nr_remote_nodes']

      self._jobs = self.NestedDotDict(dct_last_state['jobs'])
      for job_id, job in self._jobs.items():
        current_state = job.pop('state_machine_current_state', self.SUB_STATE.CHOOSE_NODE)
        self.state_machine_api_init(
          name=job.job_name,
          state_machine_transitions=self._prepare_job_state_transition_map(job_id),
          initial_state=current_state,
          on_successful_step_callback=self.__save_state
        )

      self._collected_data = dct_last_state['collected_data']
      self._golden_payload_kwargs = dct_last_state['golden_payload_kwargs']

      if self._golden_payload_kwargs is not None:
        self.create_golden_payload()

      self.input_shards = dct_last_state['input_shards']

      self.__critical_failure = dct_last_state['critical_failure']
      self._unused_configured_nodes = dct_last_state['unused_configured_nodes']

      self.state_machine_api_destroy(name=self.__state_machine_name)
      self.state_machine_api_init(
        name=self.__state_machine_name,
        state_machine_transitions=self._prepare_main_state_machine_transitions(),
        initial_state=dct_last_state['chain_dist_state'],
        on_successful_step_callback=self.__save_state
      )
      self.dct_persistent_data = dct_last_state['persistent_data']
    return

  def on_close(self):
    super(BaseChainDistPlugin, self).on_close()

    for job_id in self._jobs:
      if self._jobs[job_id].in_progress and 'node' in self._jobs[job_id] and self._get_job_state_machine_state(job_id) not in [self.SUB_STATE.CLOSED_JOB, self.SUB_STATE.WAITING_CLOSING_CONFIRMATION]:
        self.P("DEBUG: closing active job {} on {}".format(self._jobs[job_id].job_name, self._jobs[job_id].node), color='r')
        self._send_close_job_command(job_id)
        self._jobs[job_id].in_progress = False
        self._jobs[job_id].chain_dist_state = self.SUB_STATE.CLOSED_JOB
    self.__save_state()
    
    if self.__get_chain_dist_state() == self.STATE.S5_FINISHED:
      self.__delete_state()
    return

  # Job lifecycle callbacks
  def _prepare_job_state_transition_map(self, job_id):
    job_state_transition_map = {
      self.SUB_STATE.CHOOSE_NODE: {
        'STATE_CALLBACK': partial(self._maybe_choose_node, job_id),
        'TRANSITIONS': [
          {
            'NEXT_STATE': self.SUB_STATE.WAITING_START_CONFIMATION,
            'TRANSITION_CONDITION': partial(self._node_chosen, job_id),
            'ON_TRANSITION_CALLBACK': partial(self._send_config_to_node, job_id)
          }
        ],
      },
      self.SUB_STATE.WAITING_START_CONFIMATION: {
        'STATE_CALLBACK': self.state_machine_api_callback_do_nothing,
        'TRANSITIONS': [
          {
            'NEXT_STATE': self.SUB_STATE.JOB_PROGRESS,
            'TRANSITION_CONDITION': partial(self._job_started_successfully, job_id),
            'ON_TRANSITION_CALLBACK': self.state_machine_api_callback_do_nothing
          },
          {
            'NEXT_STATE': self.SUB_STATE.WAITING_CLOSING_CONFIRMATION,
            'TRANSITION_CONDITION': partial(self._job_failed_at_start, job_id),
            'ON_TRANSITION_CALLBACK': partial(self._send_close_job_command, job_id)
          },
        ],
      },
      self.SUB_STATE.JOB_PROGRESS: {
        'STATE_CALLBACK': self.state_machine_api_callback_do_nothing,
        'TRANSITIONS': [
          {
            'NEXT_STATE': self.SUB_STATE.JOB_PROGRESS,
            'TRANSITION_CONDITION': partial(self._job_in_progress_and_healthy, job_id),
            'ON_TRANSITION_CALLBACK': self.state_machine_api_callback_do_nothing
          },
          {
            'NEXT_STATE': self.SUB_STATE.WAITING_CLOSING_CONFIRMATION,
            'TRANSITION_CONDITION': partial(self._job_ready_to_be_closed, job_id),
            # this can also save the results
            'ON_TRANSITION_CALLBACK': partial(self._send_close_job_command, job_id)
          },
        ],
      },
      self.SUB_STATE.WAITING_CLOSING_CONFIRMATION: {
        'STATE_CALLBACK': self.state_machine_api_callback_do_nothing,
        'TRANSITIONS': [
          {
            'NEXT_STATE': self.SUB_STATE.CLOSED_JOB,
            'TRANSITION_CONDITION': partial(self._received_ack_or_timeout, job_id),
            'ON_TRANSITION_CALLBACK': self.state_machine_api_callback_do_nothing
          },
        ],
      },
      self.SUB_STATE.CLOSED_JOB: {
        'STATE_CALLBACK': self.state_machine_api_callback_do_nothing,
        'TRANSITIONS': [
          {
            'NEXT_STATE': self.SUB_STATE.CLOSED_JOB,
            'TRANSITION_CONDITION': self.state_machine_api_callback_always_false,
            'ON_TRANSITION_CALLBACK': self.state_machine_api_callback_do_nothing
          }
        ],
      },
    }

    return job_state_transition_map

  def _maybe_choose_node(self, job_id):
    job = self._jobs[job_id]

    if job.get('node') is not None:
      return

    if len(self._unused_configured_nodes) > 0:
      node = self._unused_configured_nodes.pop(0)

    else:
      # TODO: remove this after testing
      if True:
        possible_nodes = self.netmon.network_top_n_avail_nodes(2 * self._nr_remote_nodes, min_gpu_capability=0, verbose=0, permit_less=True)

        assigned_nodes = []
        for __job in self._jobs.values():
          if __job.get('node') is not None:
            assigned_nodes.append(__job.node)
        # end for get assigned nodes

        possible_nodes = [node for node in possible_nodes if node not in assigned_nodes]

        if len(possible_nodes) > 0:
          rnd = self.np.random.randint(0, len(possible_nodes))
          node = possible_nodes[rnd]
        else:
          node = None
      else:
        node = self.e2_addr

    if node is not None:
      job.node = node
      job.status = 'ASSIGNED'

    return

  def _node_chosen(self, job_id):
    job = self._jobs[job_id]
    return job.get('node') is not None

  def _send_config_to_node(self, job_id):
    job = self._jobs[job_id]

    config_plugin = self.generate_node_plugin_configuration(self.input_shards[job_id], job.node)

     # TODO: job.node is an address, we need to get the node_id
    node_id = self.netmon.network_node_eeid(job.node)
    pipeline_name = job.job_name
    signature = config_plugin[self.ct.BIZ_PLUGIN_DATA.SIGNATURE]
    instance_id = self.cfg_node_default_instance_id
    
    instance_config = config_plugin[self.ct.BIZ_PLUGIN_DATA.INSTANCES][0]

    job.pipeline = self._session.create_pipeline(
      node=node,
      name=pipeline_name,
      data_source=self.cfg_node_pipeline_config['stream_type'],
      config=self.cfg_node_pipeline_config,
    )

    job.instance = job.pipeline.create_plugin_instance(
      signature=signature,
      instance_id=instance_id,
      config=instance_config,
      on_data=partial(self._job_on_data_callback, job_id),
      on_notification=partial(self._job_on_notification_callback, job_id),
    )

    job.pipeline.deploy(wait_confirmation=False)

    self.on_node_start(job_id, {k: v for k, v in job.items() if not isinstance(v, dict)})
    self.P(f"DEBUG: starting job {job.job_name} on {job.node}..", color='y')
    return

  def _job_on_data_callback(self, job_id, pipeline, payload):
    job = self._jobs[job_id]
    job.last_payload_time = self.time()
    
    job.progress = payload.get('PROGRESS', 0)
    data = payload.get('DATA', None) or payload.get('RESOURCE', None)
    
    # if no useful payload, return
    if data is None:
      return

    # if we do not process the data in real time, we just append it to the job data
    job.data.append(data)

    return

  def _job_on_notification_callback(self, job_id, pipeline, notification):
    # TODO: maybe process notifications from the node
    job = self._jobs[job_id]
    job.last_payload_time = self.time()

    if notification['NOTIFICATION_TYPE'] == self.const.NOTIFICATION_TYPE.STATUS_ABNORMAL_FUNCTIONING:
      # TODO: maybe declare this node as down
      pass
    
    if notification['NOTIFICATION_TYPE'] == self.const.NOTIFICATION_TYPE.STATUS_EXCEPTION:
      job.failed = True
      self._create_error_notification(
        msg=f"Job {job.job_name} on {job.node} failed with exception. Aborting job.",
        info=notification['INFO']
      )
      self.P(f"DEBUG: job {job.job_name} on {job.node} failed with exception. Aborting job.", color='r')
    return

  def _job_started_successfully(self, job_id):
    job = self._jobs[job_id]

    job_pipeline_start_ok = False
    job_pipeline_start_fail = False

    job_instance_start_ok = False
    job_instance_start_fail = False

    if job.instance.was_last_operation_successful is not None:
      job_instance_start_ok = job.instance.was_last_operation_successful
      job_instance_start_fail = not job_instance_start_ok

    if job.pipeline.was_last_operation_successful is not None:
      job_pipeline_start_ok = job.pipeline.was_last_operation_successful
      job_pipeline_start_fail = not job_pipeline_start_ok

    job_started_ok = job_pipeline_start_ok and job_instance_start_ok
    job_started_fail = job_pipeline_start_fail or job_instance_start_fail

    return job_started_ok and not job_started_fail

  def _job_failed_at_start(self, job_id):
    job = self._jobs[job_id]
    
    job_pipeline_start_ok = False
    job_pipeline_start_fail = False

    job_instance_start_ok = False
    job_instance_start_fail = False
    
    if job.instance.was_last_operation_successful is not None:
      job_instance_start_ok = job.instance.was_last_operation_successful
      job_instance_start_fail = not job_instance_start_ok

    if job.pipeline.was_last_operation_successful is not None:
      job_pipeline_start_ok = job.pipeline.was_last_operation_successful
      job_pipeline_start_fail = not job_pipeline_start_ok

    job_started_ok = job_pipeline_start_ok and job_instance_start_ok
    job_started_fail = job_pipeline_start_fail or job_instance_start_fail

    return job_started_fail and not job_started_ok

  def _job_in_progress_and_healthy(self, job_id):
    job = self._jobs[job_id]

    job_has_progress = job.get('progress') is not None
    job_in_progress = job_has_progress and job.progress < 100
    last_payload_was_too_long_ago = self.time() - job.last_payload_time > self.cfg_node_timeout
    job_is_healthy = job.failed is False

    if last_payload_was_too_long_ago:
      job.failed = True

    return job_has_progress and job_in_progress and not last_payload_was_too_long_ago and job_is_healthy

  def _job_ready_to_be_closed(self, job_id):
    # the job is done or is not healthy
    return not self._job_in_progress_and_healthy(job_id)

  def _not_received_close_ack_and_not_timeout(self, job_id):
    return not self._received_ack_or_timeout(job_id)

  def _received_ack_or_timeout(self, job_id):
    job = self._jobs[job_id]

    command_result = job.pipeline.was_last_operation_successful

    # TODO: this is buggy -- handle case when command is not received
    # return command_result is not None and command_result
    return True

  def _maybe_save_job_results(self, job_id):
    job = self._jobs[job_id]
    if job.get('progress', 0) >= 100:
      self._dct_finished_jobs[job_id] = True
      self._collected_data[job_id] = job.data

    return

  def _send_close_job_command(self, job_id):
    job = self._jobs[job_id]

    # we want to save the results before closing the job
    # because if we restart the master, the job will be restarted as well
    self._maybe_save_job_results(job_id)

    self.on_node_stop(job_id, {k: v for k, v in job.items() if not isinstance(v, dict)})

    job.pipeline.close(wait_confirmation=False)
    return

  def _get_job_state_machine_state(self, job_id):
    return self.state_machine_api_get_current_state(name=self._jobs[job_id].job_name)

  # Job lifecycle management
  def __get_in_progress_jobs(self):
    return [index for index, job in self._jobs.items() if job.in_progress and not self._dct_finished_jobs[index]]

  def __get_unassigned_jobs(self):
    return [index for index, job in self._jobs.items() if not job.in_progress]

  def __get_failed_jobs(self):
    not_finished_jobs = [index for index, job in self._jobs.items() if not self._dct_finished_jobs[index]]
    failed_jobs = [index for index in not_finished_jobs if self._get_job_state_machine_state(index) == self.SUB_STATE.CLOSED_JOB]
    return failed_jobs

  def __reset_job(self, job_id):
    self._jobs[job_id] = self.NestedDotDict()
    self._jobs[job_id].status = 'UNASSIGNED'
    self._jobs[job_id].in_progress = False
    self._jobs[job_id].job_name = self._stream_id + f"_w_{job_id}"
    self._jobs[job_id].data = []
    self._jobs[job_id].failed = False
    self._jobs[job_id].unprocessed_data = []

    self._dct_finished_jobs[job_id] = False
    self._collected_data[job_id] = []

    self.state_machine_api_destroy(name=self._jobs[job_id].job_name)

    self.state_machine_api_init(
      name=self._jobs[job_id].job_name,
      state_machine_transitions=self._prepare_job_state_transition_map(job_id),
      initial_state=self.SUB_STATE.CHOOSE_NODE,
      on_successful_step_callback=self.__save_state
    )
    return

  def __assign_jobs(self):
    in_progress_jobs = self.__get_in_progress_jobs()

    if len(in_progress_jobs) < self.nr_remote_nodes:
      unassigned_jobs = self.__get_unassigned_jobs()

      # assign state machines to the unassigned jobs
      remaining_seats = self.nr_remote_nodes - len(in_progress_jobs)
      for job_id in unassigned_jobs[:remaining_seats]:
        self._jobs[job_id].in_progress = True
        in_progress_jobs.append(job_id)
    # endif add more jobs to tracking

  def __step_state_assigned_jobs(self):
    in_progress_jobs = self.__get_in_progress_jobs()

    for job_id in in_progress_jobs:
      job = self._jobs[job_id]
      self.state_machine_api_step(name=job.job_name)
    return

  def __reset_state_failed_jobs(self):
    failed_jobs = self.__get_failed_jobs()
    for job_id in failed_jobs:
      job_name = self._jobs[job_id].job_name
      job_node = self._jobs[job_id].node
      self.P(f"Job {job_name} on {job_node} failed. Starting again", color='r')
      self.__reset_job(job_id)
    return

  def _distribute_jobs(self):
    self.__assign_jobs()

    self.__step_state_assigned_jobs()
  
    self.__reset_state_failed_jobs()
    return

  # Master state machine
  def _prepare_main_state_machine_transitions(self):
    return {
      self.STATE.S1_DECIDE_NR_REMOTE_NODES: {
        'STATE_CALLBACK': self._choose_nr_remote_nodes,
        'TRANSITIONS': [
          {
            'NEXT_STATE': self.STATE.S2_SPLIT_INPUT,
            'TRANSITION_CONDITION': (lambda: self._nr_remote_nodes is not None),
            'ON_TRANSITION_CALLBACK': self.state_machine_api_callback_do_nothing
          }
        ],
      },
      self.STATE.S2_SPLIT_INPUT: {
        'STATE_CALLBACK': self._split_input,
        'TRANSITIONS': [
          {
            'NEXT_STATE': self.STATE.S3_DISTRIBUTE_JOBS,
            'TRANSITION_CONDITION': (lambda: self._no_inputs > 0),
            'ON_TRANSITION_CALLBACK': self.state_machine_api_callback_do_nothing
          }
        ],
      },
      self.STATE.S3_DISTRIBUTE_JOBS: {
        'STATE_CALLBACK': self._distribute_jobs,
        'TRANSITIONS': [
          {
            'NEXT_STATE': self.STATE.S4_AGGREGATE_COLLECTED_DATA,
            'TRANSITION_CONDITION': self._finish_condition,
            'ON_TRANSITION_CALLBACK': self.state_machine_api_callback_do_nothing
          },
          {
            'NEXT_STATE': self.STATE.S5_FINISHED,
            'TRANSITION_CONDITION': self._abort_job,
            'ON_TRANSITION_CALLBACK': self.state_machine_api_callback_do_nothing
          }
        ],
      },
      self.STATE.S4_AGGREGATE_COLLECTED_DATA: {
        'STATE_CALLBACK': self._aggregate_collected_data_and_compute_golden_payload,
        'TRANSITIONS': [
          {
            'NEXT_STATE': self.STATE.S5_FINISHED,
            'TRANSITION_CONDITION': self._is_golden_payload_computed,
            'ON_TRANSITION_CALLBACK': self.state_machine_api_callback_do_nothing
          },
          {
            'NEXT_STATE': self.STATE.S1_DECIDE_NR_REMOTE_NODES,
            'TRANSITION_CONDITION': self._start_another_iteration,
            'ON_TRANSITION_CALLBACK': self._reset_to_initial_state
          }
        ],
      },
      self.STATE.S5_FINISHED: {
        'STATE_CALLBACK': self.state_machine_api_callback_do_nothing,  # TODO: maybe delete cached state
        'TRANSITIONS': [
          {
            'NEXT_STATE': self.STATE.S5_FINISHED,
            'TRANSITION_CONDITION': self.state_machine_api_callback_always_false,
            'ON_TRANSITION_CALLBACK': self.state_machine_api_callback_do_nothing
          }
        ],
      },
    }

  def __get_chain_dist_state(self):
    return self.state_machine_api_get_current_state(name=self.__state_machine_name)

  def _choose_nr_remote_nodes(self):
    # logic of the current state
    if self.cfg_nr_remote_nodes is not None and self.cfg_nodes is not None:
      if self.cfg_nr_remote_nodes != len(self.cfg_nodes):
        self.P("WARNING: number of nodes is different from the specified nodes. " +
               "The behavior is as follows: the number of nodes is the number in " +
               "the `NR_REMOTE_NODES` field, the specified nodes will be prioritized " +
               "in distributing this job, and the remaining open slots, if any, will " +
               "be filled with nodes chosen by the plugin", color='r')

    if self.cfg_nr_remote_nodes is not None:
      # if number of nodes is defined in config, use it
      self._nr_remote_nodes = self.cfg_nr_remote_nodes

    elif self.cfg_nodes is not None:
      # if the nodes are specified in config, use their number
      self._nr_remote_nodes = len(self.cfg_nodes)
    else:
      # otherwise, use default of 4 nodes
      self._nr_remote_nodes = self.cfg_default_nr_remote_nodes

    return

  def _split_input_in_thread(self):
    self.input_shards = self.split_input()
    return

  # TODO: review
  # how do we split data based on node performance?
  # how do we handle when a good node fails?
  def _split_input(self):
    if self.__split_input_thread is None:
      self.__split_input_thread = threading.Thread(target=self._split_input_in_thread)
      self.__split_input_thread.start()

    # timeout is 8 because the biz thread is forcefully if blocked for 10 seconds
    self.__split_input_thread.join(timeout=8)

    if not self.__split_input_thread.is_alive():
      # the thread finished working, so we can continue
      self.__split_input_thread = None

      for i in range(self._no_inputs):
        self.__reset_job(i)
      # prepare the jobs for the new input shards

    else:
      self.P("Split input thread is still running", color='r')

    return

  def _aggregate_collected_data(self, collected_data):
    if self.__aggregate_collected_data_thread is None:
      self.__aggregate_collected_data_thread = threading.Thread(
        target=self.aggregate_collected_data,
        kwargs={
          'collected_data': collected_data
        },
      )
      self.__aggregate_collected_data_thread.start()

    self.__aggregate_collected_data_thread.join(timeout=8)

    if not self.__aggregate_collected_data_thread.is_alive():
      # the thread finished working, so we can continue
      self.__aggregate_collected_data_thread = None

    else:
      self.P("Merge output thread is still running", color='r')
    return

  def _start_another_iteration(self):
    return self.start_another_iteration()

  def _reset_to_initial_state(self):
    self._dct_finished_jobs = {}
    self._jobs = self.NestedDotDict()
    self._collected_data = {}
    if self.cfg_nodes is not None:
      self._unused_configured_nodes = [node for node in self.cfg_nodes]

    self.input_shards = []
    self.dct_state_timestamps = {}
    return

  @property
  def _no_inputs(self):
    return len(self.input_shards)

  @property
  def _progress_by_node(self):
    progress_by_node = {k: {'NODE': v.get('node'), 'PROGRESS': v.get('progress', 0)}
                          for k, v in self._jobs.items()}
    return progress_by_node

  def _is_golden_payload_computed(self):
    return self._golden_payload is not None

  def _finish_condition(self):
    complete_results_at_the_end = len(self._collected_data) == self._no_inputs
    return complete_results_at_the_end

  def _abort_job(self):
    return self.__critical_failure

  def _aggregate_collected_data_and_compute_golden_payload(self):
    dct_sorted_collected_data = dict(sorted(self._collected_data.items()))

    collected_data = [data for data in dct_sorted_collected_data.values()]
    assert len(collected_data) == self._no_inputs, "Not all input shards have been processed"

    self._aggregate_collected_data(collected_data)

  def _compute_state_time_details_for_status_payload(self):
    dct_state_time_details = {}

    lst_ended_states = list(self.dct_state_timestamps.keys())
    for i in range(len(lst_ended_states) - 1):
      key = lst_ended_states[i] + '_start_time'
      dct_state_time_details[key] = self.dct_state_timestamps[lst_ended_states[i]]['start_date']

      key = lst_ended_states[i] + '_elapsed_time'
      start_time = self.datetime.timestamp(self.dct_state_timestamps[lst_ended_states[i]]['start_date'])
      end_time = self.datetime.timestamp(self.dct_state_timestamps[lst_ended_states[i + 1]]['start_date'])
      elapsed_time = str(self.timedelta(seconds=int(end_time - start_time)))

      dct_state_time_details[key] = elapsed_time
    # endfor

    # compute the last state
    key = lst_ended_states[-1] + '_start_time'
    dct_state_time_details[key] = self.dct_state_timestamps[lst_ended_states[-1]]['start_date'].strftime(
      '%Y-%m-%d %H:%M:%S.%f')

    key = lst_ended_states[-1] + '_elapsed_time'
    start_time = self.datetime.timestamp(self.dct_state_timestamps[lst_ended_states[-1]]['start_date'])
    end_time = self.time()
    elapsed_time = str(self.timedelta(seconds=int(end_time - start_time)))

    dct_state_time_details[key] = elapsed_time

    key = lst_ended_states[-1] + '_remaining_time'
    dct_state_time_details[key] = "Not yet implemented"

    return dct_state_time_details

  def _custom_status_payload(self):
    dct = self.custom_status_payload()
    if not isinstance(dct, dict):
      return {}

    dct = {k.upper(): v for k, v in dct.items()}
    return dct

  def _maybe_create_status_payload(self):
    payload = None

    too_long_since_last_sent = self.time() - self._last_time_ping_send > self.cfg_ping_send_period_max
    too_soon_since_last_sent = self.time() - self._last_time_ping_send < self.cfg_ping_send_period_min
    progress_changed = self._last_sent_progress != self.avg_progress(self._collected_data)

    progress_status = progress_changed and not too_soon_since_last_sent and not self._is_golden_payload_computed()
    finished_status = progress_changed and self._is_golden_payload_computed()

    if too_long_since_last_sent or progress_status or finished_status:
      self._last_time_ping_send = self.time()
      self._last_sent_progress = self.avg_progress(self._collected_data)

      if self._is_golden_payload_computed():
        payload = self._golden_payload
      elif self.avg_progress(self._collected_data) != 100:
        # if the progress is 100, we wait for the golden payload to be computed
        payload = self._create_payload(
          progress=self.avg_progress(self._collected_data),
          progress_by_node=self._progress_by_node,

          start_date=self.datetime.fromtimestamp(self.first_process_time).strftime(
            '%Y-%m-%d %H:%M:%S.%f') if self.first_process_time is not None else None,
          elapsed_time=str(self.timedelta(seconds=int(self.time_alive))),
          # Remaining time should be computed based on the progress
          # Which means that we need a method to compute a progress status for each state
          # And eventually a method to estimate time duration for each state

          # For this reason, until we have this, we will not try to compute the remaining time
          remaining_time="Not yet implemented",
          **self._custom_status_payload(),
          # TODO: remaining_time="",

          state=self.__get_chain_dist_state(),
          # **self.__compute_state_time_details_for_status_payload(),
        )

    if payload is not None:
      debug_progress_by_node = ', '.join([
        f"{v['NODE']}:{v['PROGRESS']:.02f}"
        for v in self._progress_by_node.values()
      ])

      msg = 'Job state {} | {:.02f}%% done, {} shards: {}'.format(
        self.__get_chain_dist_state(),
        self.avg_progress(self._collected_data),
        self.nr_remote_nodes,
        debug_progress_by_node
      )
      self.P(msg)
    return payload

  def _maybe_save_start_time_of_state(self):
    """
    Save the start time of the current state if it is not already saved.
    The saved time is used to compute the elapsed time of the current state.
    """
    current_state = self.__get_chain_dist_state(),
    if current_state not in self.dct_state_timestamps:
      self.dct_state_timestamps[current_state] = {
        'start_date': self.datetime.now(),
      }
    return

  def _process(self):
    self._maybe_save_start_time_of_state()

    self.state_machine_api_step(self.__state_machine_name)

    payload = self._maybe_create_status_payload()

    return payload

  def _on_config(self):
    self._choose_nr_remote_nodes()
    return

  # Public methods
  @property
  def nr_remote_nodes(self):
    """
    The number of nodes to use. This is the number of shards to split the input into.

    Returns
    -------
    int
        The number of nodes.
    """
    return self._nr_remote_nodes

  def create_golden_payload(self, **kwargs):
    """
    Create the golden payload. This method must be called in the `self.aggregate_collected_data` method.
    """

    kwargs = {k.upper(): v for k, v in kwargs.items()}

    if self._golden_payload_kwargs is None:
      self._golden_payload_kwargs = {
        'progress': 100,
        **kwargs
      }
    self._golden_payload = self._create_payload(
      **self._golden_payload_kwargs,

        start_date=self.datetime.fromtimestamp(self.first_process_time).strftime(
            '%Y-%m-%d %H:%M:%S.%f') if self.first_process_time is not None else None,
      elapsed_time=str(self.timedelta(seconds=int(self.time_alive))),

      remaining_time=str(self.timedelta(seconds=0)),

      # **self.__compute_state_time_details_for_status_payload(),
    )
    return

  def start_another_iteration(self):
    """
    This method must return True if the plugin should start another iteration. The new iteration will start from the beginning.
    This method must return False if the plugin should stop.

    Returns
    -------
    bool 
        True if another iteration should be started, False otherwise. Default is False.
    """
    return False

  # Customizable Logic
  @abstractclassmethod
  def split_input(self):
    """
    This method must split the input data into shards and store them in the `self.input_shards` list.
    This method can take as long as it needs
    This method should return a list that will contain all the inputs that can be processed by the nodes.
    """
    raise NotImplementedError

  @abstractclassmethod
  def aggregate_collected_data(self, collected_data):
    """
    Merge the output of the nodes. This method must call the `self.create_golden_payload` method.

    Parameters
    ----------
    collected_data : list
        List of data from the nodes. The list elements are in the order expected order.
    """
    raise NotImplementedError

  def generate_node_plugin_configuration(self, input_shard, node_id):
    # TODO: make this method return only the instance config
    config_plugin = {
      'SIGNATURE': self.cfg_node_signature,
      'INSTANCES': [{
        'INSTANCE_ID': self.cfg_node_default_instance_id,
        "MAX_INPUTS_QUEUE_SIZE": 500,
        "PROCESS_DELAY": 1,
      }]
    }

    return config_plugin

  def generate_node_pipeline_configuration(self, input_shard, node_id):
    config_pipeline = {}

    return config_pipeline

  def on_node_start(self, job_id, job):
    """
    Callback method called when `job_id` job running on `job['node']` started.

    Parameters
    ----------
    job_id : int
        The index of the job.
    job : dict
        The job data.
    """
    return

  def on_node_stop(self, job_id, job):
    """
    Callback method called when `job_id` job running on `job['node']` stopped.

    Parameters
    ----------
    job_id : int
        The index of the job.
    job : dict
        The job data.
    """
    return

  def avg_progress(self, collected_data):
    """
    Compute the average progress on all input shards.

    Parameters
    ----------
    collected_data : dict
        The data collected from the nodes up until this point.

    Returns
    -------
    float
        The average progress of the job.
    """
    lst = [v.get('progress', 0) for v in self._jobs.values()]
    avg_progress = self.np.mean(lst)
    return avg_progress

  def custom_status_payload(self):
    """
    This method returns a dictionary with custom status payload fields.
    """
    return {}

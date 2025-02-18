"""
Stream configuration:
{
    "CAP_RESOLUTION": 20,
    "LIVE_FEED": false,
    "NAME": "iris_distributed",
    "PLUGINS": [
        {
            "INSTANCES": [
                {
                    "INSTANCE_ID": "default"
                }
            ],
            "SIGNATURE": "a_dummy_job_map_reduce"
        }
    ],
    "RECONNECTABLE": "KEEPALIVE",
    "TYPE": "a_dummy_dataframe_map_reduce",
    "STREAM_CONFIG_METADATA" : {
        "NR_WORKERS" : 2
    },
    "URL": "https://gist.githubusercontent.com/netj/8836201/raw/6f9306ad21398ea43cba4f7d537619d0e07d5ae3/iris.csv"
}
"""

from naeural_core.business.base import BasePluginExecutor as BaseClass


_CONFIG = {
  **BaseClass.CONFIG,

  'RESEND_GOLDEN' : False,

  # Jobs should have a bigger inputs queue size, because they have to process everything
  'MAX_INPUTS_QUEUE_SIZE': 1000,

  # Allow empty inputs in order to send pings from time to time
  'ALLOW_EMPTY_INPUTS': True,

  'VALIDATION_RULES' : {
    **BaseClass.CONFIG['VALIDATION_RULES'],
  },

}

__VER__ = '0.1.0'

class ADummyJobMapReducePlugin(BaseClass):

  def on_init(self):
    self._lst_workers = None
    self._started_jobs = {}
    self._gathered_progress = {}
    self._gathered_results = {}
    self._golden_payload = None
    return

  @property
  def cfg_resend_golden(self):
    return self._instance_config.get('RESEND_GOLDEN', False)

  def _generate_worker_plugin_configuration(self):
    config_plugin = {
      'SIGNATURE' : 'a_dummy_job',
      'INSTANCES' : [{
        'INSTANCE_ID' : 'default'
      }]
    }

    return config_plugin

  @property
  def avg_progress(self):
    lst = [self._gathered_progress.get(x, {}).get('PROGRESS', 0) for x in self._lst_workers]
    avg_progress = self.np.mean(lst)
    return avg_progress

  def _phase_map(self):
    metadata = self.dataapi_all_metadata()
    struct_data = self.dataapi_struct_data()
    lst_chunks = struct_data['chunks']
    self._lst_workers = metadata['workers']
    if len(lst_chunks) != len(self._lst_workers):
      payload = self._create_payload(
        stage=self.const.STAGE_SEARCH_WORKERS, started_jobs=self._started_jobs
      )
      return payload
    #endif

    # send command to each worker
    for i, (chunk, worker) in enumerate(list(zip(lst_chunks, self._lst_workers))):
      config_plugin = self._generate_worker_plugin_configuration()
      name = metadata['workers_stream_name'][worker]
      self._started_jobs[worker] = name

      self.cmdapi_start_stream_by_params_on_other_box(
        box_id=worker,
        name=name,
        url=chunk,
        stream_type='a_dummy_dataframe',
        reconnectable="KEEPALIVE", live_feed=False,
        plugins=[config_plugin],
        **metadata.get('WORKER_STREAM_CONFIG', {}),
      )
    #endfor

    return

  def _phase_reduce(self):
    # the stream will stay in the reduce phase until it is told to be closed.
    # Be careful that after finishing their jobs, workers may still send 'PING' payloads.
    # these 'PING' payloads arrive also in this method.
    # Even though a command is sent to stop the worker stream (and implicitly the job plugin), 
    # one such 'PING' still may arrive before the command is executed.

    if self._golden_payload is not None:
      # that's why this protection is set. _golden_payload should be populated when everything is done
      return

    struct_data = self.dataapi_struct_data()
    metadata = self.dataapi_all_metadata()
    sender_id = struct_data['EE_ID']
    self._gathered_progress[sender_id] = {'PROGRESS': struct_data['PROGRESS']}
    self._gathered_results[sender_id] = struct_data.get('ALL_INFERENCES', None)

    self.P("DEBUG progress from workers:\n{}".format(self._gathered_progress))

    if self.avg_progress < 100:
      # the workers still process their jobs!
      payload = self._create_payload(progress=self.avg_progress, progress_by_worker=self._gathered_progress)
      return payload
    #endif

    # if arriving here, then all workers finished their jobs!

    # reunite inferences (or videos for blurring case...)
    indexes = metadata['input_indexes']
    inferences_from_all_workers = {}
    for i, worker in enumerate(self._lst_workers):
      all_inferences = self._gathered_results[worker]
      worker_start_chunk, worker_end_chunk = indexes[i]
      real_frames_interval = list(range(worker_start_chunk, worker_end_chunk))

      # the frames indexes come as string in 'ALL_INFERENCES'
      frames_interval = list(map(lambda x: str(x), list(all_inferences.keys())))

      dct_frame_translation = dict(zip(frames_interval, real_frames_interval))

      for k, v in all_inferences.items():
        inferences_from_all_workers[dct_frame_translation[k]] = v
      #endfor
    #endfor

    payload = self._create_payload(progress=self.avg_progress, all_inferences=inferences_from_all_workers)
    self._golden_payload = payload

    # the plugin will not receive input from now on, thus a process delay could be added (auto-slowdown)
    self._instance_config['PROCESS_DELAY'] = 2

    # stop the current stream acquisition - it is still alive in order to keep alive this plugin,
    # but it will not read anymore from the communication channel
    self.cmdapi_finish_current_stream_acquisition()

    for box_id, stream_name in self._started_jobs.items():
      # archive the jobs streams as they are not needed anymore - everything was gathered from workers
      self.cmdapi_archive_stream_on_other_box(box_id=box_id, stream_name=stream_name)

    return payload

  def _process(self):
    if self.dataapi_received_input():
      metadata = self.dataapi_all_metadata()
      if metadata['phase'] == 'map':
        return self._phase_map()
      elif metadata['phase'] == 'reduce':
        return self._phase_reduce()
      #endif
    else:
      # no input from the stream. Here are 2 options:
      # i) the stream finished the acquisition;
      # ii) due to the fact that the plugin allows empty inputs, it runs on empty inputs :)
      payload = None
      if self._golden_payload is not None:
        # it means that progress is 100, so the stream finished the acquisition
        if self.cfg_resend_golden:
          payload = self._golden_payload
        elif self.time() - self.last_payload_time >= 20:
          payload = self._create_payload(ping=True)
      return payload
    #endif
    return
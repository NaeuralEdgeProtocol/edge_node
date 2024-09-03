from PyE2 import Payload, Session

from core.business.default.web_app.fast_api_web_app import FastApiWebAppPlugin as BasePlugin
from extensions.business.utils.ai4e_utils import AI4E_CONSTANTS, Job, get_job_config, job_data_to_id

__VER__ = '0.1.0.0'

_CONFIG = {
  **BasePlugin.CONFIG,
  'USE_NGROK': False,
  'NGROK_ENABLED': False,
  'NGROK_DOMAIN': None,
  'NGROK_EDGE_LABEL': None,

  'SAVE_PERIOD': 60,
  'REQUEST_TIMEOUT': 10,

  'PORT': 5000,
  'ASSETS': '_ai4everyone',
  'VALIDATION_RULES': {
    **BasePlugin.CONFIG['VALIDATION_RULES'],
  },
}


class AI4EveryonePlugin(BasePlugin):
  CONFIG = _CONFIG

  def __init__(self, **kwargs):
    super(AI4EveryonePlugin, self).__init__(**kwargs)
    self.jobs_data = {}
    self.requests_responses = {}
    self.last_persistence_save = self.time()
    self.request_cache = {}
    # !!!This approach, although works, will not be allowed in the future because it's not safe
    self.session = Session(
      name=f'{self.str_unique_identification}',
      config=self.global_shmem['config_communication']['PARAMS'],
      log=self.log,
      bc_engine=self.global_shmem[self.ct.BLOCKCHAIN_MANAGER],
      on_payload=self.on_payload,
    )
    return

  def on_init(self):
    super(AI4EveryonePlugin, self).on_init()
    self.jobs_data = self.load_persistence_data()
    return

  """SESSION SECTION"""
  if True:
    def on_payload(self, sess: Session, node_id: str, pipeline: str, signature: str, instance: str, payload: Payload):
      if signature.lower() not in AI4E_CONSTANTS.RELEVANT_PLUGIN_SIGNATURES:
        return
      is_status = payload.data.get('IS_STATUS', False)
      if is_status:
        self.maybe_update_job_data(node_id, pipeline, signature, instance, payload)
      else:
        self.register_request_response(node_id, pipeline, signature, instance, payload)
      return

    def maybe_update_job_data(self, node_id: str, pipeline: str, signature: str, instance: str, payload: Payload):
      job_id = job_data_to_id(node_id, pipeline, signature, instance)
      if job_id not in self.jobs_data:
        self.jobs_data[job_id] = Job(
          session=self.session, job_id=job_id,
          node_id=node_id, pipeline=pipeline,
          signature=signature, instance=instance
        )
      job = self.jobs_data[job_id]
      job.maybe_update_data(
        data=payload.data,
        pipeline=pipeline,
        signature=signature
      )
      return

    def register_request_response(self, node_id: str, pipeline: str, signature: str, instance: str, payload: Payload):
      request_id = payload.data.get('REQUEST_ID')
      if request_id is None:
        return
      self.requests_responses[request_id] = payload
      return

    def send_request(self, job: Job, **kwargs):
      request_id = self.uuid()
      status, msg = job.send_instance_command(
        REQUEST_ID=request_id,
        **kwargs
      )
      return status, msg, request_id

    def process_request(self, job: Job, **request_kwargs):
      status, msg, request_id = self.send_request(job, **request_kwargs)
      if not status:
        return False, {"error": f"Failed to send request: {msg}"}
      request_ts = self.time()
      while self.time() - request_ts <= self.cfg_request_timeout and request_id not in self.requests_responses:
        self.sleep(0.1)
      if request_id not in self.requests_responses:
        return False, {"error": "Request timed out"}
      response = self.requests_responses.pop(request_id)
      return True, response.data

    def cache_request_data(self, job_id, data_id, data):
      if job_id not in self.request_cache:
        self.request_cache[job_id] = {}
      # endif job_id not in cache
      if data_id not in self.request_cache[job_id]:
        self.request_cache[job_id][data_id] = {}
      # endif data_id not in cache
      self.request_cache[job_id][data_id] = {**data}
      return

    def get_cached_request_data(self, job_id, data_id):
      return self.request_cache.get(job_id, {}).get(data_id)

    def process_sample_request(self, job: Job, handle_votes=False, vote_required=False):
      request_kwargs = {'SAMPLE_DATAPOINT': True} if vote_required else {'SAMPLE': True}
      success, response_data = self.process_request(job, **request_kwargs)
      if not success:
        return success, response_data
      sample_filename = response_data.get('SAMPLE_FILENAME')
      if sample_filename is None:
        return False, {"error": "Sample not found"}
      img = response_data.get('IMG')
      cache_kwargs = {
        'img': img
      }
      if img is not None:
        if handle_votes:
          votes = response_data.get('VOTES')
          cache_kwargs['votes'] = votes
        # endif handle votes
        current_data = self.get_cached_request_data(job.job_id, sample_filename)
        new_data = {} if current_data is None else current_data
        new_data = {**new_data, **cache_kwargs}
        self.cache_request_data(job.job_id, data_id=sample_filename, data=new_data)
      # endif img is not None
      res = {"name": sample_filename, "content": img}
      if handle_votes:
        res['classes'] = job.classes
      # endif handle votes
      return True, res

    def data_to_response(self, data: dict, mandatory_fields=['img']):
      processed_data = {k.lower(): v for k, v in data.items()}
      mandatory_fields = [field.lower() for field in mandatory_fields]
      for field in mandatory_fields:
        if field not in processed_data:
          return False, {"error": f"`{field}` not found in data."}
      # endfor mandatory fields

      res = {'content': processed_data.get('img')}
      if 'votes' in processed_data:
        res['votes'] = processed_data.get('votes')
      return True, res

    def process_filename_request(self, job: Job, filename: str, force_refresh: bool = False):
      if not force_refresh:
        # Check if the data is cached
        cached_data = self.get_cached_request_data(
          job_id=job.job_id,
          data_id=filename
        )
        if cached_data is not None:
          return self.data_to_response(cached_data)
      # endif not force_refresh
      success, response_data = self.process_request(job, FILENAME=filename, FILENAME_REQUEST=True)
      if not success:
        return success, response_data
      return self.data_to_response(response_data)

    def start_job(self, body: dict):
      job_id = self.uuid()
      node_addr = body.get('nodeAddress', self.node_id)
      job_config = get_job_config(job_id, body, self.now_str())
      pipeline_name = f'cte2e_{job_id}'
      self.session.create_pipeline(
        node_id=node_addr,
        name=pipeline_name,
        data_source="VOID",
        plugins=[job_config]
      ).deploy()
  """END SESSION SECTION"""

  """ENDPOINTS SECTION"""
  if True:
    @BasePlugin.endpoint
    def jobs(self):
      return [job.to_msg() for job in self.jobs_data.values()]

    @BasePlugin.endpoint
    def job(self, job_id):
      if job_id in self.jobs_data:
        return self.jobs_data[job_id].to_msg()
      return None

    @BasePlugin.endpoint(method="post")
    def create_job(self, body: dict):
      # Extract the data from the body
      node_addr = body.get('nodeAddress')
      name = body.get('name')
      desc = body.get('description')
      self.P(f'Received job creation request for {node_addr}: `{name}` - `{desc}`')
      return self.start_job(body)

    @BasePlugin.endpoint(method="post")
    def stop_job(self, job_id, body: dict):
      if job_id in self.jobs_data:
        success, result = self.jobs_data[job_id].stop_acquisition()
        return result if success else None
      return None

    @BasePlugin.endpoint(method="post")
    def publish_job(self, job_id, body: dict):
      if job_id in self.jobs_data:
        success, result = self.jobs_data[job_id].publish_job()
        return result if success else None
      return None

    @BasePlugin.endpoint(method="post")
    def vote(self, job_id, body: dict):
      if job_id in self.jobs_data:
        success, result = self.jobs_data[job_id].send_vote(body)
        return result if success else None
      return None

    @BasePlugin.endpoint(method="post")
    def stop_labeling(self, job_id, body: dict):
      if job_id in self.jobs_data:
        success, result = self.jobs_data[job_id].stop_labeling()
        return result if success else None
      return None

    @BasePlugin.endpoint(method="post")
    def publish_labels(self, job_id, body: dict):
      if job_id in self.jobs_data:
        success, result = self.jobs_data[job_id].publish_labels()
        return result if success else None
      return None
    """
    @BasePlugin.endpoint(method="post")
    def delete_job(self, job_id):
      pass  # TODO
    """

    @BasePlugin.endpoint(method="get")
    def job_status(self, job_id):
      if job_id in self.jobs_data:
        return self.jobs_data[job_id].get_status()
      return None

    @BasePlugin.endpoint(method="get")
    def labeling_status(self, job_id):
      if job_id in self.jobs_data:
        return self.jobs_data[job_id].get_labeling_status()
      return None

    @BasePlugin.endpoint(method="get")
    def data_sample(self, job_id):
      if job_id in self.jobs_data:
        success, result = self.process_sample_request(self.jobs_data[job_id])
        return result if success else None
      return None

    @BasePlugin.endpoint(method="get")
    def data_filename(self, job_id, filename):
      if job_id in self.jobs_data:
        success, result = self.process_filename_request(self.jobs_data[job_id], filename=filename)
        return result if success else None
      return None

    @BasePlugin.endpoint(method="get")
    def datapoint(self, job_id):
      if job_id in self.jobs_data:
        success, result = self.process_sample_request(self.jobs_data[job_id], handle_votes=True)
        return result if success else None
      return None

    @BasePlugin.endpoint(method="get")
    def datapoint_sample(self, job_id):
      if job_id in self.jobs_data:
        success, result = self.process_sample_request(self.jobs_data[job_id], handle_votes=True, vote_required=True)
        return result if success else None
      return None

    @BasePlugin.endpoint(method="get")
    def datapoint_filename(self, job_id, filename):
      if job_id in self.jobs_data:
        success, result = self.process_filename_request(self.jobs_data[job_id], filename=filename)
        return result if success else None
      return None

    @BasePlugin.endpoint(method="get")
    def baseclasses(self):
      return self.get_available_first_stage_classes()

    @BasePlugin.endpoint
    def datasourcetypes(self):
      return self.get_available_data_source_types()

    @BasePlugin.endpoint
    def stage2classifiers(self):
      return self.get_available_model_architectures()

  """END ENDPOINTS SECTION"""

  """ADDITIONAL SECTION"""
  if True:
    def get_available_first_stage_classes(self):
      return AI4E_CONSTANTS.FIRST_STAGE_CLASSES

    def get_available_model_architectures(self):
      return AI4E_CONSTANTS.AVAILABLE_ARCHITECTURES

    def get_available_data_source_types(self):
      return AI4E_CONSTANTS.AVAILABLE_DATA_SOURCES
  """END ADDITIONAL SECTION"""

  """PERIODIC SECTION"""
  if True:
    def maybe_persistence_save(self):
      if self.time() - self.last_persistence_save > self.cfg_save_period:
        self.last_persistence_save = self.time()
        saved_data = {}
        for job_id, job in self.jobs_data.items():
          saved_data[job_id] = job.get_persistence_data()
        # endfor jobs
        self.persistence_serialization_save(saved_data)
      # endif save time
      return

    def load_persistence_data(self):
      res = {**self.jobs_data}
      saved_data = self.persistence_serialization_load()
      if saved_data is None:
        return res
      for key, data in saved_data.items():
        if key not in res:
          node_id, pipeline = data.get('node_id'), data.get('pipeline')
          signature, instance = data.get('signature'), data.get('instance_id')
          res[key] = Job(
            session=self.session, job_id=key,
            node_id=node_id, pipeline=pipeline,
            signature=signature, instance=instance
          )
        res[key].load_persistence_data(data)
      # endfor saved_data
      return res
  """END PERIODIC SECTION"""

  def process(self):
    super(AI4EveryonePlugin, self).process()
    self.maybe_persistence_save()
    return


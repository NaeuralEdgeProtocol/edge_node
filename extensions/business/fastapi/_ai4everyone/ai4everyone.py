from core.business.base.web_app import FastApiWebAppPlugin as BasePlugin
from PyE2 import Session, Payload
from extensions.business.utils.ai4e_utils import job_data_to_id, Job, get_job_config, AI4E_CONSTANTS

__VER__ = '0.1.0.0'

_CONFIG = {
  **BasePlugin.CONFIG,
  'USE_NGROK': False,
  'NGROK_DOMAIN': None,
  'NGROK_EDGE_LABEL': None,

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
    self.session = Session(
      name=f'{self.str_unique_identification}',
      config=self.global_shmem['config_communication']['PARAMS'],
      log=self.log,
      bc_engine=self.global_shmem[self.ct.BLOCKCHAIN_MANAGER],
      on_payload=self.on_payload,
    )
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
      job.maybe_update_data(payload.data)
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
      while request_id not in self.requests_responses:
        self.sleep(0.1)
      response = self.requests_responses.pop(request_id)
      return True, response.data

    def process_sample_request(self, job: Job):
      success, response_data = self.process_request(job, SAMPLE=True)
      if not success:
        return success, response_data
      return True, {"name": response_data.get('SAMPLE_FILENAME')}

    def process_filename_request(self, job: Job, filename: str):
      success, response_data = self.process_request(job, FILENAME=filename)
      if not success:
        return success, response_data
      img = response_data.get('IMG')
      return (True, {"content": img}) if img is not None else (False, {"error": "Image not found"})

    def start_job(self, body: dict):
      job_id = self.uuid()
      node_addr = body.get('nodeAddress')
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

    @BasePlugin.endpoint(method="get")
    def job_status(self, job_id):
      if job_id in self.jobs_data:
        return self.jobs_data[job_id].get_status()
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

  def process(self):
    super(AI4EveryonePlugin, self).process()

    # do your stuff
    return


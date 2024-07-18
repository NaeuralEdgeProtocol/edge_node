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
      self.P(signature)
      if signature.lower() not in AI4E_CONSTANTS.RELEVANT_PLUGIN_SIGNATURES:
        return
      self.update_job_data(node_id, pipeline, signature, instance, payload)
      return

    def update_job_data(self, node_id: str, pipeline: str, signature: str, instance: str, payload: Payload):
      job_id = job_data_to_id(node_id, pipeline, signature, instance)
      if job_id not in self.jobs_data:
        self.jobs_data[job_id] = Job(job_id, node_id, pipeline, signature, instance)
      job = self.jobs_data[job_id]
      job.update_data(payload.data)
      return

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


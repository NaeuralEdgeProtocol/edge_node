from core.business.base.fastapi import BaseFastapiPlugin as Base
from core.business.base.fastapi import _CONFIG as BASE_CONFIG

_CONFIG = {
  **BASE_CONFIG,
  'ASSETS' : 'people_counting',
  'OBJECT_TYPE' : [ 'person' ],
  'DETECTOR_PROCESS_DELAY' : 0.2,
  'STATUS_UPDATE_INTERVAL' : 2,
  'VALIDATION_RULES': {
    **BASE_CONFIG['VALIDATION_RULES'],
  },
}

class PCCt:
  R_URL = 'url'
  R_DONE = 'done'
  R_PC = 'people_count'
  R_T_START = 'started'
  R_PIPE_NAME = 'name'
  K_DONE = 'done'
  K_PC = 'people_count'

class FastapiPeopleCounting01Plugin(Base):
  CONFIG = _CONFIG

  def __init__(self, **kwargs):
    self._people_count = 0
    super(FastapiPeopleCounting01Plugin, self).__init__(**kwargs)
    return

  def get_jinja_template_args(self) -> dict:
    return {
      **super(FastapiPeopleCounting01Plugin, self).get_jinja_template_args()
    }

  def on_init(self):
    super(FastapiPeopleCounting01Plugin, self).on_init()
    self.P("Running post-init setup for people counting")
    # Dict with url -> answer, done
    self.request_data = {}
    return

  @Base.endpoint
  def get_people_count(self, url):
    info = self.request_data.get(url)
    if info is not None:
      # We've already started a request for this url.
      return {
        PCCt.R_URL : url,
        PCCt.R_PC : info[PCCt.K_PC],
        PCCt.R_DONE : info[PCCt.K_DONE]
      }
    #endif
    pipe_name =  str(self.uuid(10))
    self.request_data[url] = {
      PCCt.R_URL : url,
      PCCt.R_URL : False,
      PCCt.R_PC : 0,
      PCCt.R_T_START : self.time(),
      PCCt.R_PIPE_NAME : pipe_name
    }

    pipeline_name = self._stream_id
    signature_name = self._signature
    instance_name = self.get_instance_id()

    worker_code = f"""
pipeline_name = "{pipeline_name}"
signature_name = "{signature_name}"
instance_name = "{instance_name}"
if not hasattr(self, 'people'):
  self.people = {{}}
if not hasattr(self, 'lasttime'):
  self.lasttime = self.time()
if not hasattr(self, 'received_input'):
  self.received_input = False

if self.dataapi_received_input():
  self.received_input = True

if self.dataapi_image_inferences() is not None:
  for detection in self.dataapi_image_inferences():
    if not detection['IS_TRUSTED']:
      continue
    self.people[detection['TRACK_ID']] = detection['PROB_PRC']
done = (len(self.dataapi_stream_info()) == 0) and self.received_input
if done or self.time() - self.lasttime > {self.cfg_status_update_interval}:
  command = {{
    'url' : "{url}",
    'done' : done,
    'people_count' : len(self.people.keys())
  }}
  self.cmdapi_send_instance_command(
    pipeline=pipeline_name,
    signature=signature_name,
    instance_id=instance_name,
    instance_command=command
  )
  self.lasttime = self.time()
result = {{}}
"""

    worker_code = self.code_to_base64(worker_code, verbose=False)

    plugin = {
      "INSTANCES" : [
        {
          "AI_ENGINE"   : "lowres_general_detector",
          "CODE"      : worker_code,
          "SIGNATURE" : "CUSTOM_EXEC_01",
          "INSTANCE_ID" : "inst01",
          "PROCESS_DELAY": self.cfg_detector_process_delay,
          "object_type": self.cfg_object_type,
        }
      ],
      "SIGNATURE" : "CUSTOM_EXEC_01"
    }

    pipeline_config = {
      "NAME" : pipe_name,
      "LIVE_FEED" : False,
      "PLUGINS" : [
        plugin
      ],
      "URL" : url,
      "TYPE": "VideoFile",
      "RECONNECTABLE" : False
    }

    # Raise on self for now though we could theoretically raise it on another
    # node,
    self.cmdapi_start_pipeline(pipeline_config)

    return {
      PCCt.R_URL : url,
      PCCt.R_PC : 0,
      PCCt.R_DONE : False,
    }

  def _on_command(self, data, **kwargs):
    url = data.get(PCCt.R_URL)
    done = data.get(PCCt.R_DONE)
    people_count = data.get(PCCt.R_PC)
    if url is None or done is None or people_count is None:
      # Ignore misformed requests.
      return
    self.request_data[url][PCCt.R_PC] = people_count
    self.request_data[url][PCCt.R_DONE] = done
    return

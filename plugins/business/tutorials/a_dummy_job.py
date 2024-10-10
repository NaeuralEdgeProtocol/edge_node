"""
Stream configuration:
{
    "CAP_RESOLUTION": 20,
    "LIVE_FEED": false,
    "NAME": "iris",
    "PLUGINS": [
        {
            "INSTANCES": [
                {
                    "INSTANCE_ID": "default"
                }
            ],
            "SIGNATURE": "a_dummy_job"
        }
    ],
    "RECONNECTABLE": "KEEPALIVE",
    "TYPE": "a_dummy_dataframe",
    "URL": "https://gist.githubusercontent.com/netj/8836201/raw/6f9306ad21398ea43cba4f7d537619d0e07d5ae3/iris.csv"
}
"""


from naeural_core.business.base import BasePluginExecutor as BaseClass
from time import time

_CONFIG = {
  **BaseClass.CONFIG,



  'AI_ENGINE': 'a_dummy_ai_engine',
  'OBJECT_TYPE': [],

  # Jobs should have a bigger inputs queue size, because they have to process everything
  'MAX_INPUTS_QUEUE_SIZE': 1000,

  # Allow empty inputs in order to send pings from time to time
  'ALLOW_EMPTY_INPUTS': True,

  'RESEND_GOLDEN': False,

  'VALIDATION_RULES': {
    **BaseClass.CONFIG['VALIDATION_RULES'],
  },
}

__VER__ = '0.1.0'


class ADummyJobPlugin(BaseClass):
  
  def on_init(self):
    self._dct_inferences = {}
    self._golden_payload = None
    self._sent_progresses = []
    return

  @property
  def cfg_resend_golden(self):
    return self._instance_config.get('RESEND_GOLDEN', False)

  def process(self):
    if self.dataapi_received_input():
      # received input from the stream
      metadata = self.dataapi_input_metadata()
      inferences = self.dataapi_struct_data_inferences()
      crt_inference = [inferences[0]['pred'], inferences[0]['cnt'], inferences[0]['inp']]
      progress = 100 * ((metadata['idx'] + 1) / metadata['length'])
      self._dct_inferences[metadata['idx']] = crt_inference

      payload = None
      kwargs_payload = dict(idx=metadata['idx'], length=metadata['length'], progress=progress)
      integer_progress = int(progress)
      if integer_progress == 100:
        payload = self._create_payload(all_inferences=self._dct_inferences, **kwargs_payload)
        self._golden_payload = payload
        # the plugin will not receive input from now on, thus a process delay could be added
        self._instance_config['PROCESS_DELAY'] = 2
        self.P("Progress 100%", color='g')
        self._sent_progresses.append(integer_progress)
      elif integer_progress % 10 == 0 and integer_progress not in self._sent_progresses:
        # send a progress payload from time to time. If sending many progress payloads, be careful that if using
        # in a map-reduce setup, the master map-reduce stream should have a bigger cap resolution!!!

        # 2 progresses can have the same value when converting to int and therefore we track the send progresses
        payload = self._create_payload(crt_inferece=crt_inference, **kwargs_payload)
        self._sent_progresses.append(integer_progress)
      # endif

    else:
      # no input from the stream. Here are 2 options:
      # i) the stream finished the acquisition;
      # ii) due to the fact that the plugin allows empty inputs, it runs on empty inputs :)
      payload = None
      if self._golden_payload is not None:
        # it means that progress is 100, so the stream finished the acquisition
        if self.cfg_resend_golden:
          payload = self._golden_payload
        elif time() - self.last_payload_time >= 20:
          payload = self._create_payload(ping=True)
    # endif

    return payload

"""
{
    "CAP_RESOLUTION": 1,
    "LIVE_FEED": true,
    "NAME": "TS_REST_AND_OTHER",
    "PLUGINS": [

        {
            "INSTANCES": [
                {
                    "INSTANCE_ID": "DEFAULT"
                }
            ],
            "SIGNATURE": "A_DUMMY_FEATURE"
        }
        
    ],
    "RECONNECTABLE": true,
    "STREAM_CONFIG_METADATA": {},
    "TYPE": "ADummyStructStream", 
    "## or TYPE": "ADummyStream", 
    "URL": ""
}  
  
"""
from naeural_core.business.base import BasePluginExecutor

__VER__ = '0.1.0.0'

_CONFIG = {
  **BasePluginExecutor.CONFIG,
  'VALIDATION_RULES': {
    **BasePluginExecutor.CONFIG['VALIDATION_RULES'],
  },

  'AI_ENGINE'     : 'test1_model_aleator',
  'PRAG' : 10000,
  'OBJECT_TYPE'   : [],
  'PROCESS_DELAY' : 1,
  
}

class Test1BizAleatorPlugin(BasePluginExecutor):
  CONFIG = _CONFIG
  def __init__(self, **kwargs):
    super(Test1BizAleatorPlugin, self).__init__(**kwargs)
    return
  
  @property
  def cfg_prag(self):
    return self._instance_config['PRAG']
  
  def _process(self):
    model_data = self.dataapi_inferences()
    
    val = model_data['test1_model_aleator'][0][0]
    if val > self.cfg_prag:
      is_alert = True
    else:
      is_alert = False
    raw_data = self.dataapi_struct_data()
    metadata = self.dataapi_all_metadata()
    payload = self._create_payload(
      plugin_predict=model_data,
      plugin_data=raw_data,
      plugin_metadata=metadata,
      is_alert=is_alert,
    )
    return payload

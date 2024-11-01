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


from naeural_core.business.base import BasePluginExecutor as BasePlugin

import os
import sys


__VER__ = '0.1.0.0'

_CONFIG = {

  # mandatory area
  **BasePlugin.CONFIG,

  # our overwritten props
  'PROCESS_DELAY' : 1,

  'LOG_MESSAGE'   : '',

  'VALIDATION_RULES' : {
    **BasePlugin.CONFIG['VALIDATION_RULES'],    
  },  

}

class ADummyFeatureInvalidPlugin(BasePlugin):

  def process(self):
    import time
    payload = None
    self.P(self.cfg_log_message)
    time.sleep(10)
    return payload

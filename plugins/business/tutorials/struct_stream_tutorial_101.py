# -*- coding: utf-8 -*-
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
            "SIGNATURE": "STRUCT_STREAM_TUTORIAL_101"
        }
        
    ],
    "RECONNECTABLE": true,
    "STREAM_CONFIG_METADATA": {},
    "TYPE": "StructStreamTutorial",
    "URL": ""
}  
  
"""


from core.business.base import BasePluginExecutor as BasePlugin


__VER__ = '0.1.0.0'

_CONFIG = {
  # mandatory area
  **BasePlugin.CONFIG,
  # end of mandatory area

  # our overwritten props
  'AI_ENGINE'     : 'a_dummy_ai_engine',
  'PROCESS_DELAY' : 10,
  
  'EXTRA_DEBUG'   : False,
}

class StructStreamTutorial101Plugin(BasePlugin):
  
  def on_init(self):    
    default = {
      'COUNTER'         : 0,
      'LAST_SAVE'       : None, 
    }    
    self.__object = self.cacheapi_load_json(default=default)
    self.__object['CURRENT_START'] = self.time_to_str()
    self.P("Plugin started from state: {}".format(self.__object))
    return
  
  def _maybe_do_some_serialization_stuff(self):
    if self.np.random.randint(0, 100) < 10:
      self.P("Checking last state and saving new state")
      last_state = self.cacheapi_load_json()
      self.P("  Last state: {}".format(last_state))
      self.__object['COUNTER'] += 1
      self.__object['LAST_SAVE'] = self.time_to_str()
      self.cacheapi_save_json(self.__object)
      self.P("  Plugin saved state: {}".format(self.__object))
    return
  
  def process(self):
    # get the raw data
    input_data = self.dataapi_inputs()
    # get the struct data out of the raw data
    struct_data = self.dataapi_struct_data()
    # get the metadata
    metadata = self.dataapi_all_metadata()
    # get all the inferences
    all_inferences = self.dataapi_inferences()
    predict_data = self.dataapi_inference_results()
    
    data_struct=dict(
        input_data=input_data,
        struct_data=struct_data,
        metadata=metadata,
        all_inferences=all_inferences,
        predict_data=predict_data,        
    )

    payload = self._create_payload(
      data_struct=data_struct,
    )    
    
    if self.cfg_extra_debug:
      self.P("Plugin data:\n{}".format(self.json_dumps(data_struct, indent=4)))
    
    self._maybe_do_some_serialization_stuff()
    return payload
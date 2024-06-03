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


from core.business.base import BasePluginExecutor as BasePlugin


__VER__ = '0.1.0.0'

_CONFIG = {
  # mandatory area
  **BasePlugin.CONFIG,
  # end of mandatory area

  # our overwritten props
  'AI_ENGINE'     : 'a_dummy_ai_engine',
  'PROCESS_DELAY' : 5,

}

class ADummyFeaturePlugin(BasePlugin):
  
  def process(self):
    input_data = self.dataapi_inputs()
    struct_data = self.dataapi_struct_data()
    metadata = self.dataapi_all_metadata()
    all_inferences = self.dataapi_inferences()
    predict_data = self.dataapi_inference_results()

    payload = self._create_payload(
      data_struct=dict(
        input_data=input_data,
        struct_data=struct_data,
        metadata=metadata,
        all_inferences=all_inferences,
        predict_data=predict_data,        
      )
    )    
    return payload
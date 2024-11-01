"""
Demo for a plugin that uses a OnDemandInput as pipeline data acquisition.

Example pipeline configuration:
{
    "CAP_RESOLUTION": 20,
    "NAME": "on-demand-test",
    "PLUGINS": [
        {
            "INSTANCES": [
                {
                    "AI_ENGINE"   : "a_sum_model",
                    "INSTANCE_ID": "default"
                }
            ],
            "SIGNATURE": "on_demand_plugin_example"
        }
    ],
    "TYPE": "OnDemandInput",
    "STREAM_CONFIG_METADATA" : {
      "SERVER_SIDE_PARAMS_HERE" : "1234"
    },
    "URL": 0
}

then:

{ 
  "ACTION" : "PIPELINE_COMMAND",  
  "PAYLOAD" : {
    "NAME": "on-demand-test",
    "PIPELINE_COMMAND" : {
      "PAYLOAD_CONTEXT" : { "info" : "some info"},
      "STRUCT_DATA" : [[10,20], [1,2]]
    }
  }
}



"""


from naeural_core.business.base import BasePluginExecutor as BaseClass

_CONFIG = {
  **BaseClass.CONFIG,
  
  'ALLOW_EMPTY_INPUTS' : False,

  'VALIDATION_RULES' : {
    **BaseClass.CONFIG['VALIDATION_RULES'],
  },  
}

__VER__ = '0.1.0'

class OnDemandPluginExamplePlugin(BaseClass):
  CONFIG = _CONFIG
  def __init__(self, **kwargs):
    ver = kwargs.get('version', __VER__)
    super(OnDemandPluginExamplePlugin, self).__init__( **kwargs)
    return


  def startup(self):
    super().startup()
    return
  

  def _process(self):
    # received input from the stream      
    full_input = self.dataapi_full_input()
    str_dump = self.json_dumps(full_input, indent=2)
    self.P("Received input from pipeline:\n{}".format(str_dump))
    stream_metadata = self.dataapi_stream_metadata()
    inputs = self.dataapi_inputs()
    data = self.dataapi_struct_data()
    inputs_metadata = self.dataapi_input_metadata()
    inferences = self.dataapi_struct_data_inferences()    
    payload = self._create_payload(
      data=data,
      inferences=inferences,
    )
    return payload

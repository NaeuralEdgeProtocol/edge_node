"""
Demo for a plugin that only sends the data from the pipeline DCT and the serving (if any).


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

class ASimplePluginPlugin(BaseClass):
 
  def process(self):
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

from core.business.base import BasePluginExecutor as BasePlugin


__VER__ = '0.1.0.0'

_CONFIG = {

  # mandatory area
  **BasePlugin.CONFIG,

  # our overwritten props
  'AI_ENGINE'               : "code_generator",
  'OBJECT_TYPE'             : [],
  'PROCESS_DELAY'           : 10,
  'ALLOW_EMPTY_INPUTS'      : False, # if this is set to true the on-idle will be triggered continously the process
  

  'VALIDATION_RULES' : {
    **BasePlugin.CONFIG['VALIDATION_RULES'],
  },  
}

class CodeAssist01Plugin(BasePlugin):
  
  CONFIG = _CONFIG

  def __init__(self, **kwargs):
    ver = kwargs.get('version', __VER__)
    super(CodeAssist01Plugin, self).__init__( **kwargs)
    return

  def _process(self):
    # we always receive input from the upstream due to the fact that _process
    # is called only when we have input based on ALLOW_EMPTY_INPUTS=False
    full_input = self.dataapi_full_input()
    self.P("Processing received input: {}".format(full_input)) 
    str_dump = self.json_dumps(full_input, indent=2)
    self.P("Received input from pipeline:\n{}".format(str_dump))
    stream_metadata = self.dataapi_stream_metadata()
    inputs = self.dataapi_inputs()
    data = self.dataapi_struct_data()
    inputs_metadata = self.dataapi_input_metadata()
    inferences = self.dataapi_struct_data_inferences()
    text_responses = [inf.get('text') for inf in inferences]
    model_name = inferences[0].get('MODEL_NAME', None) if len(inferences) > 0 else None
    payload = self._create_payload(
      data=data,
      inferences=inferences,
      request_id=data.get('request_id', None),
      text_responses=text_responses,
      model_name=model_name,
    )
    return payload

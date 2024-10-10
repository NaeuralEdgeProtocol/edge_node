import numpy as np

from naeural_core.serving.base import ModelServingProcess as BaseServingProcess

__VER__ = '0.1.0.0'

_CONFIG = {
  **BaseServingProcess.CONFIG,
  'VALIDATION_RULES': {
    **BaseServingProcess.CONFIG['VALIDATION_RULES'],
  },

  "PICKED_INPUT" : "STRUCT_DATA",
  
  "RUNS_ON_EMPTY_INPUT" : False,
}

class Test1ModelAleator(BaseServingProcess):
  CONFIG = _CONFIG
  def __init__(self, **kwargs):
    super(Test1ModelAleator, self).__init__(**kwargs)
    return
  
  def _startup(self):
    return

  def _pre_process(self, inputs):    
    lst_inputs = inputs.get('DATA', [])
    preprocessed = []
    for inp in lst_inputs:
      preprocessed.append(inp.get('numar') if isinstance(inp, dict) else None)
    return preprocessed

  def _predict(self, inputs):
    dummy_result = []
    for inp in inputs:
      # for each stream input      
      dummy_result.append(np.array([inp + 1]))
    dummy_result = np.array(dummy_result)
    return dummy_result

  def _post_process(self, preds):
    result = preds.tolist()
    return result
  
  
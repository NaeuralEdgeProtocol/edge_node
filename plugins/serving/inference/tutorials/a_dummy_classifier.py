from core.serving.base import ModelServingProcess as BaseServingProcess

__VER__ = '0.1.0.0'

_CONFIG = {
  **BaseServingProcess.CONFIG,
  
  "CRASH_PREDICT" : -100, # default value instead of `None`

  "CRASH_PREPROC" : -10,

  "CRASH_POSTPROC" : -1,
  
  "TEST_INFERENCE_PARAM" : 0,
  

  "PICKED_INPUT" : "STRUCT_DATA",
  
  "RUNS_ON_EMPTY_INPUT" : False,

  'VALIDATION_RULES': {
    **BaseServingProcess.CONFIG['VALIDATION_RULES'],
    
    "CRASH_PREDICT" : {
      "TYPE" : "int",
      "MIN"  : 0,
      "MAX"  : 1000,
    },
  
    "CRASH_PREPROC" : {
      "TYPE" : "int",
      "MIN"  : 0,
      "MAX"  : 1000,
    },
  
    "CRASH_POSTPROC" : {
      "TYPE" : "int",
      "MIN"  : 0,
      "MAX"  : 1000,
    },
    
  },

}

class ADummyClassifier(BaseServingProcess):

  def __crash_simulator(self, thr):
    if thr > 0:
      if self._counter > thr:
        self.P("Self-crashing at iter {}".format(self._counter), color='error')
        while True:
          self.sleep(1)
      elif self._counter in [thr // 3, thr//2, thr // 1.5]:
        self.P("Self-crashind in {} iters".format(thr - self._counter), color='error')
    
    return

  
  def on_init(self):
    self._counter = 0
    # check some params that can be re-configured from biz plugins or (lower priority) 
    # serving env in config_startup.txt
    if self.cfg_crash_preproc > 0:
      self.P("Self-crashing programmed at pre-proc iter {}".format(self.cfg_crash_preproc), color='error')
    else:
      self.P("CRASH_PREPROC={}".format(self.cfg_crash_preproc))
    if self.cfg_crash_predict > 0:
      self.P("Self-crashing programmed at predict iter {}".format(self.cfg_crash_predict), color='error')
    else:
      self.P("CRASH_PREDICT={}".format(self.cfg_crash_predict))
    if self.cfg_crash_postproc > 0:
      self.P("Self-crashing programmed at post-proc iter {}".format(self.cfg_crash_postproc), color='error')
    else:
      self.P("CRASH_POSTPROC={}".format(self.cfg_crash_postproc))
    return
  
    
  def pre_process(self, inputs): 
    debug = False
    lst_inputs = inputs.get('DATA', [])
    serving_params = inputs.get('SERVING_PARAMS', [])
    if len(serving_params) > 0:
      if isinstance(serving_params[0], dict):
        debug = serving_params[0].get('SHOW_EXTRA_DEBUG', False)
      if debug:
        self.P("Inference step info:\n - Detected 'SERVING_PARAMS': {}\n - Inputs: {}".format(
          self.json_dumps(serving_params, indent=4), 
          self.json_dumps(inputs, indent=4)
        ))
    preprocessed = []
    for i, inp in enumerate(lst_inputs):
      params = serving_params[i].get('TEST_INFERENCE_PARAM', None) if i < len(serving_params) else None
      preprocessed.append([
          inp.get('OBS') if isinstance(inp, dict) else 0,
          params,
        ]
      )
    self.__crash_simulator(self.cfg_crash_preproc)
    return preprocessed
  

  def predict(self, inputs):
    self.__crash_simulator(self.cfg_crash_predict)
    self._counter += 1
    dummy_result = []
    for inp in inputs:
      # for each stream input    
      input_data = inp[0]
      input_params = inp[1]  
      model = lambda x: int(round(x)) % 2 == 0
      dummy_result.append(
        [model(input_data), self._counter, input_data, input_params]
      )
    dummy_result = self.np.array(dummy_result)
    return dummy_result


  def post_process(self, preds):
    self.__crash_simulator(self.cfg_crash_postproc)
    result = [{'pred': x[0], 'cnt': x[1], 'inp':x[2], 'cfg':x[3]} for x in preds]
    return result
  
  
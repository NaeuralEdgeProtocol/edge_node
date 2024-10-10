from naeural_core.serving.base import ModelServingProcess as BaseServingProcess

__VER__ = '0.1.0.0'

_CONFIG = {
  **BaseServingProcess.CONFIG,
  
  "CRASH_PREDICT" : -1, # default value instead of `None`

  "CRASH_PREPROC" : -1,

  "CRASH_POSTPROC" : -1,
  
  "TEST_INFERENCE_PARAM" : 0,
  

  "PICKED_INPUT" : "IMG",
  
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

class ADummyCvClassifier(BaseServingProcess):
  
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
    if self.cfg_crash_predict > 0:
      self.P("Self-crashing programmed at predict iter {}".format(self.cfg_crash_predict), color='error')
    if self.cfg_crash_postproc > 0:
      self.P("Self-crashing programmed at post-proc iter {}".format(self.cfg_crash_postproc), color='error')
    return
  
    
  def pre_process(self, inputs): 
    lst_inputs = inputs.get('DATA', [])
    serving_params = inputs.get('SERVING_PARAMS', [])
    preprocessed = []
    for i, inp in enumerate(lst_inputs):
      params = serving_params[i].get('TEST_INFERENCE_PARAM', None) if i < len(serving_params) else None
      preprocessed.append([
          # some kind of img preproc
          inp if isinstance(inp, self.np.ndarray) else self.np.zeros((100,100,3)), # assume each input is img
          params,
        ]
      )
    self.__crash_simulator(self.cfg_crash_preproc)
    return preprocessed
  

  def predict(self, inputs):
    self.__crash_simulator(self.cfg_crash_predict)
    dummy_result = []
    for inp in inputs:
      # for each stream input      
      self._counter += 1
      img = inp[0]
      predict_param = inp[1]
      obs_result = (img.sum() + predict_param, self._counter, img.shape[0], img.shape[1])
      dummy_result.append(obs_result)
    dummy_result = self.np.array(dummy_result)
    return dummy_result

  def post_process(self, preds):
    self.__crash_simulator(self.cfg_crash_postproc)
    result = [{'pred': x[0], 'cnt': x[1], 'inp':x[2], 'cfg':x[3]} for x in preds]
    return result
  
  
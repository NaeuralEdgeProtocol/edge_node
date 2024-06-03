"""
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
            "SIGNATURE": "a_simple_plugin"
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
      "STRUCT_DATA" : [1,2,3,4]
    }
  }
}


"""

from core.serving.base import ModelServingProcess as BaseServingProcess

__VER__ = '0.1.0.0'

_CONFIG = {
  **BaseServingProcess.CONFIG,
  
  "CRASH_PREDICT" : -1, # default value instead of `None`

  "CRASH_PREPROC" : -1,

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

class ASumModel(BaseServingProcess):

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
      
  def _pre_process(self, inputs): 
    lst_inputs = inputs.get('DATA', [])
    self.P("Received inputs:\n{}".format(lst_inputs))
    serving_params = inputs.get('SERVING_PARAMS', [])
    if len(serving_params) > 0 and len(serving_params[0]) > 0:
      self.P("Detected 'SERVING_PARAMS': {}".format(serving_params))
    preprocessed = []
    for i, inp in enumerate(lst_inputs):
      params = serving_params[i].get('TEST_INFERENCE_PARAM', None) if i < len(serving_params) else None
      if params is not None:
        self.P("Detected obs {} 'SERVING_PARAMS': {}".format(i, serving_params))
      preprocessed.append([
          self.np.array(inp),
          params,
        ]
      )
    self.__crash_simulator(self.cfg_crash_preproc)
    return preprocessed
  

  def _predict(self, inputs):
    self.__crash_simulator(self.cfg_crash_predict)
    self._counter += 1
    result = []
    for inp in inputs:
      # for each stream input      
      data = inp[0]
      params = inp[1]
      yhat = self.np.sum(data)
      result.append((yhat, self._counter, data, params))
    
    return result

  def _post_process(self, preds):
    self.__crash_simulator(self.cfg_crash_postproc)
    result = [{'yhat': x[0], 'cnt': x[1], 'inp':x[2], 'params':x[3]} for x in preds]
    return result
  
  
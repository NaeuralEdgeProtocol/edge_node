"""
{
  "CAP_RESOLUTION": 2,
  "LIVE_FEED": true,
  "NAME": "RES_TIMESERIES",
  "PLUGINS": [
    {
      "SIGNATURE": "TIMESERIES_REST_01",
      "INSTANCES": [
        {
            "DEBUG_REST": true,
            "INSTANCE_ID": "TS_REST",
            "PROCESS_DELAY": 0.5,
            "REQUEST": {
                "DATA": {
                   "HISTORY":[1,2,3,4,5,6,7,8,9,1,2,3,4,5,6,7,8,9,0,1,2,3,4,5,6,7,8,9,1,2,3,4],
                   "STEPS":10
                },
                "TIMESTAMP": 1667543087.8323452
            }
        }
      ]
    }
  ],
  "RECONNECTABLE": true,
  "STREAM_CONFIG_METADATA": {},
  "TYPE": "ADummyStructStream",
  "URL": ""
}



"""


from core.business.base import SimpleRestExecutor as BasePlugin

__VER__ = '0.2.2'

_CONFIG = { 
  **BasePlugin.CONFIG,
  'VALIDATION_RULES' : {
    **BasePlugin.CONFIG['VALIDATION_RULES'],
  },  

  "INFO_MANIFEST" : {
    "NAME" : "Time Series Prediction on demand: Predict on min 30 val history",
    "REQUEST" :{ 
      "DATA" : {
        "HISTORY" : "min 30 values",
        "STEPS"  : "nr steps into future"
        },
      "TIMESTAMP" : "timestamp float (optional)"
      }
    }
}

class TimeseriesRest01Plugin(BasePlugin):
  CONFIG = _CONFIG
  def __init__(self, **kwargs):
    self._counter = 0
    
    super(TimeseriesRest01Plugin, self).__init__(**kwargs)
    return
  
  def _history_has_valid_data(self, history):
    valid = True
    if not isinstance(history, list):
      return False
    if len(history) <= 5:
      return False
    for h in history:
      if not isinstance(h, (int, float)):
        valid = False
    return valid
  
  def _on_request(self, request):
    yh = None
    success = False
    valid_history = None
    self.P("Received request: {} ".format(request))
    if isinstance(request, dict):
      history = request.get('HISTORY')
      steps = request.get('STEPS')
      valid_history = self._history_has_valid_data(history)
      if valid_history and isinstance(steps, int) and steps > 0:
        try:
          n_hist = len(history)
          model = self.create_basic_ts_model(series_min=n_hist-1)  
          model.fit(history)          
          yh = model.predict(steps)      
          self._counter += 1
          success = True
          self.P("Predicted {} steps on {} history".format(steps, history))
        except Exception as e:
          self.P("Exception occured:\n{}".format(
            self.get_exception()), color='r')
          yh = str(e)
      else:
        self.P("Invalid predict request received", color='r')
    response = self._create_response(
      request_status="Success" if success else "FAILURE",
      request_count=self.request_count,
      predict_count=self._counter,
      predict_result=yh if yh is not None else "Invalid request for prediction. Valid history: {}".format(valid_history),
      request=request,
    )
    return response
   
           

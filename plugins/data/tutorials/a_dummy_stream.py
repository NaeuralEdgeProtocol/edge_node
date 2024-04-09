from core import constants as ct
from core.data.base import DataCaptureThread

_CONFIG = {
  **DataCaptureThread.CONFIG,
  
  'CAP_RESOLUTION'   : 1,
  
  'VALIDATION_RULES' : {
    **DataCaptureThread.CONFIG['VALIDATION_RULES'],
  },
}

class ADummyStreamDataCapture(DataCaptureThread):
  
  def on_init(self):
    self._metadata.update(meta_dummy_count=0)
    return
  
    
  def data_step(self):
    _obs = {'OBS' : self._metadata.meta_dummy_count}
    
    self._metadata.meta_dummy_count = self._metadata.meta_dummy_count + 1
    self._add_struct_data_input(obs=_obs)
    return 
    

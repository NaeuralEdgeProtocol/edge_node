"""


"""

from naeural_core.business.base import BasePluginExecutor as BaseClass

_CONFIG = {
  **BaseClass.CONFIG,
  
  'ALLOW_EMPTY_INPUTS' : False,
  
  'ACCEPT_SELF' : False,
  
  'FULL_DEBUG_PAYLOADS' : False,

  'VALIDATION_RULES' : {
    **BaseClass.CONFIG['VALIDATION_RULES'],
  },  
}

__VER__ = '0.1.0'

class NetworkProcessorPlugin(BaseClass):
  CONFIG = _CONFIG
  
  
  def on_init(self):
    self.__handlers = {}
    # we get all the functions that start with on_payload_
    for name in dir(self):
      if name.startswith("on_payload_") and callable(getattr(self, name)):
        signature = name.replace("on_payload_", "").upper()
        self.__handlers[signature] = getattr(self, name)
        
    if len(self.__handlers) == 0:
      self.P("No payload handlers found", color="red")
    else:
      self.P("Payload handlers found for: {}".format(list(self.__handlers.keys())), color="green")
    return
  
  def get_instance_path(self):
    return [self.ee_id, self._stream_id, self._signature, self.cfg_instance_id]
  
  
  def __maybe_process_received(self):
    datas = self.dataapi_struct_datas()    
    if len(datas) > 0:
      for data in datas:
        try:
          verified = self.bc.verify(data, str_signature=None, sender_address=None)
        except Exception as e:
          self.P(f"{e}: {data}")
          continue
        if not verified:
          self.P("Payload signature verification FAILED: {}".format(data), color="red")
          continue
        payload_path = data.get(self.const.PAYLOAD_DATA.EE_PAYLOAD_PATH, [None, None, None, None])        
        if self.cfg_full_debug_payloads:
          self.P("RECV: {}".format(payload_path))
        is_self = payload_path == self.get_instance_path()
        if is_self and not self.cfg_accept_self:
          continue
        signature = payload_path[2]
        sender = data.get(self.const.PAYLOAD_DATA.EE_SENDER, None)
        if signature in self.__handlers:
          self.__handlers[data["signature"]](data)
    # end if we have payloads
    return


  def _process(self):
    self.__maybe_process_received()  
    return super()._process()

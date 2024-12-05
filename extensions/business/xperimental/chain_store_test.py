

from naeural_core.business.base import BasePluginExecutor as BaseClass

_CONFIG = {
  **BaseClass.CONFIG,
  
  'ALLOW_EMPTY_INPUTS' : False,
  
  "PROCESS_DELAY" : 5,
  
  'VALIDATION_RULES' : {
    **BaseClass.CONFIG['VALIDATION_RULES'],
  },  
}


class ChainStoreTestPlugin(BaseClass):
  CONFIG = _CONFIG  
  
  ## Move to  base_plugin
  def chainstore_set(self, key, value):
    func = self.plugins_shmem.get('__chain_storage_set')
    if func is not None:
      self.P("Setting data: {} -> {}".format(key, value), color="green")
      func(key, value)
    else:
      self.P("No chain storage set function found", color="red")
    return
  
  
  def chainstore_get(self, key):
    func = self.plugins_shmem.get('__chain_storage_get')
    if func is not None:
      value = func(key)
      self.P("Getting data: {} -> {}".format(key, value), color="green")
    else:
      self.P("No chain storage get function found", color="red")
      value = None
    return value
  
  
  @property
  def chainstorage(self):
    return self.plugins_shmem['__chain_storage']
  
  
  def get_instance_path(self):
    return [self.ee_id, self._stream_id, self._signature, self.cfg_instance_id]  
  
  # END Move to base_plugin
  
  def on_init(self):
    self.__myself = self.uuid()
    self.__shown = 0
    return
  
  
  def process(self):
    key = self.__myself
    value = self.chainstore_get(key)
    if value is None:
      self.P("My value is not in the chainstorage... setting it")
      value = ".".join(self.get_instance_path())
      self.chainstore_set(key, value)
      self.P(f"Done setting value: {key}:{value}")
    elif self.__shown < 5:
      self.P("Chainstore: \n{}".format(self.json_dumps(self.chainstorage)))
      self.__shown += 1      
    return
  
  

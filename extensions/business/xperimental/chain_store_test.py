"""
```json
{
  "TYPE" : "NetworkListener",
  "NAME" : "chain_store_test1",
  
  "PLUGINS" : [
    {
      "SIGNATURE" : "CHAIN_STORE_BASIC",
      "INSTANCES" : [
        {
          "INSTANCE_ID" : "CHAIN_STORE_MGR_1",
          "FULL_DEBUG_PAYLOADS" : true
        }
      ]
    },
    {
      "SIGNATURE" : "CHAIN_STORE_TEST",
      "INSTANCES" : [
        {
          "INSTANCE_ID" : "CHAIN_STORE_TEST_1"
        }
      ]
    }
  ]
}

{
  "TYPE" : "NetworkListener",
  "NAME" : "chain_store_test2",
  
  "PLUGINS" : [
    {
      "SIGNATURE" : "CHAIN_STORE_BASIC",
      "INSTANCES" : [
        {
          "INSTANCE_ID" : "CHAIN_STORE_MGR_2"
        }
      ]
    },
    {
      "SIGNATURE" : "CHAIN_STORE_TEST",
      "INSTANCES" : [
        {
          "INSTANCE_ID" : "CHAIN_STORE_TEST_2"
        }
      ]
    }
  ]
}
```

"""

from naeural_core.business.base import BasePluginExecutor as BaseClass

_CONFIG = {
  **BaseClass.CONFIG,
  
  'ALLOW_EMPTY_INPUTS' : False,
  
  "PROCESS_DELAY" : 60,
  
  'VALIDATION_RULES' : {
    **BaseClass.CONFIG['VALIDATION_RULES'],
  },  
}


class ChainStoreTestPlugin(BaseClass):
  CONFIG = _CONFIG  
  
  ## Move to  base_plugin
  def chainstore_set(self, key, value, debug=False):
    func = self.plugins_shmem.get('__chain_storage_set')
    if func is not None:
      if debug:
        self.P("Setting data: {} -> {}".format(key, value), color="green")
      func(key, value, debug=debug)
    else:
      if debug:
        self.P("No chain storage set function found", color="red")
    return
  
  
  def chainstore_get(self, key, debug=False):
    func = self.plugins_shmem.get('__chain_storage_get')
    if func is not None:
      value = func(key, debug=debug)
      if debug:
        self.P("Getting data: {} -> {}".format(key, value), color="green")
    else:
      if debug:
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
    self.__shown = 0
    return
  
  
  def process(self):
    key = self.get_instance_id() # some arbitrary key
    value = self.chainstore_get(key, debug=True)
    if value is None:
      self.P(f"My key '{key}' is not in the chainstorage... setting it")
      value = "VALUE-{}".format(self.get_instance_id()[-4:]) # some arbitrary value
      self.chainstore_set(key, value, debug=True)
      self.P(f"Done setting value: {key}:{value}")
    elif self.__shown < 5:
      self.P("Chainstore: \n{}".format(self.json_dumps(self.chainstorage, indent=2)))
      self.__shown += 1      
    return
  
  

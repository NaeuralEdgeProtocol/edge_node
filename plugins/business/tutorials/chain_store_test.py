"""
```json
{
  "TYPE" : "void",
  "NAME" : "cs_test1",
  
  "PLUGINS" : [
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
  "TYPE" : "Void",
  "NAME" : "cs_test2",
  
  "PLUGINS" : [
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
  
  "PROCESS_DELAY" : 10,
  
  'VALIDATION_RULES' : {
    **BaseClass.CONFIG['VALIDATION_RULES'],
  },  
}


class ChainStoreTestPlugin(BaseClass):
  CONFIG = _CONFIG  

  
  def on_init(self):
    self.__shown = 0
    self.__iter = 0
    self.__key_count = 0
    return
  
  
  def process(self):
    self.__iter += 1
    if self.__iter % 3 == 0 and self.__key_count < 9:
      self.__key_count += 1
      key = f"K{self.__key_count}-{self.node_id}-{self.uuid(4)}" # some arbitrary key
      value = self.chainstore_get(key, debug=True)
      if value is None:
        self.P(f"My key '{key}' is not in the chainstorage... setting it")
        value = f"V{self.__key_count}-{self.node_id}-{self.uuid(4)}" # some arbitrary value
        ok = self.chainstore_set(key, value, debug=True)
        if not ok:
          self.P(f"Failed to set value: {key}:{value}. Chainstore:\n{self.json_dumps(self.chainstorage, indent=2)}", color="red")
        else:
          self.P(f"Done setting value: {key}:{value}")
          
        self.P("Chainstore: \n{}\n".format(
          self.json_dumps(self._chainstorage, indent=2),
        ))
        self.__shown += 1      
    return
  
  

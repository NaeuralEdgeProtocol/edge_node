"""
{
  "TYPE" : "NetworkListener"
  "NAME" : "chain_store_test1",
  
  "PLUGINS" [
    {
      "SIGNATURE" : "CHAIN_STORE_BASIC",
      "INSTANCES" : [
        {
          "INSTANCE_ID" : "DEFAULT"
        }
      ]
    },
    {
      "SIGNATURE" : "CHAIN_STORE_TEST",
      "INSTANCES" : [
        {
          "INSTANCE_ID" : "DEFAULT"
        }
      ]
    }
  ]
}

{
  "TYPE" : "NetworkListener"
  "NAME" : "chain_store_test2",
  
  "PLUGINS" [
    {
      "SIGNATURE" : "CHAIN_STORE_BASIC",
      "INSTANCES" : [
        {
          "INSTANCE_ID" : "DEFAULT"
        }
      ]
    },
    {
      "SIGNATURE" : "CHAIN_STORE_TEST",
      "INSTANCES" : [
        {
          "INSTANCE_ID" : "DEFAULT"
        }
      ]
    }
  ]
}



"""

from plugins.business.xperimental.network_processor import NetworkProcessorPlugin as BaseClass

_CONFIG = {
  **BaseClass.CONFIG,
  
  'ALLOW_EMPTY_INPUTS' : True,
  
  "ACCEPT_SELF" : False,

  'VALIDATION_RULES' : {
    **BaseClass.CONFIG['VALIDATION_RULES'],
  },  
}

__VER__ = '0.1.0'

class ChainStoreBasicPlugin(BaseClass):
  CONFIG = _CONFIG
  
  
  def on_init(self):
    self.__chain_storage = {}
    self.__key_owners = {}
    self.__key_confirmations = self.defaultdict(int)
    self.__ops = self.deque()
    self.plugins_shmem["__chain_storage"] = self.__chain_storage
    self.plugins_shmem["__chain_storage_get"] = self._get_value
    self.plugins_shmem["__chain_storage_set"] = self._set_value
    return
  
  def _get_value(self, key):
    self.__chain_storage.get(key, None)
    return
  
  def _set_value(self, key, value, owner=None):
    if keyhash is None:
      keyhash = self.uuid()
    self.__chain_storage[key] = value
    self.__key_owners[key] = owner
    self.__ops.append({      
        "op" : "STORE",
        "key": key,        
        "value" : value,   
        "owner" : self.get_instance_path(),
    })
    return
  
  def __maybe_broadcast(self):
    while len(self.__ops) > 0:
      self.add_payload_by_fields(
        chain_store_data=self.__ops.popleft()
      )
    return
  
  def on_payload_chain_store_basic(self, payload):
    data = payload.get("chain_store_data", {})
    operation = data.get("op", None)
    if operation == "STORE":
      key = data.get("key", None)
      value = data.get("value", None)
      owner = data.get("owner", None)
      if key is None or hash is None:
        return
      if self.__chain_storage.get(key, None) == value:
        self.P(f"KV already exists owned by {owner}")
      else:
        self._set_value(key, value, owner=owner)
        
      self.add_payload_by_fields(
        chain_store_data={
          "op" : "CONFIRM",
          "key": key,
          "value" : value,
          "owner" : owner,
          "confirm_by" : self.get_instance_path(),
        }
      )
    elif operation == "CONFIRM":
      key = data.get("key", None)
      value = data.get("value", None)
      owner = data.get("owner", None)
      if owner == self.get_instance_path():
        confirm_by = data.get("confirm_by", None)
        valid = self.__chain_storage.get(key, None) == value and self.__key_owners.get(key, None) == owner
        if valid:
          self.__key_confirmations[key] += 1
          self.P(f"Key {key} confirmed by {confirm_by}. Confirmations: {self.__key_confirmations[key]}")
    return
  

  
  def process(self):
    self.__maybe_broadcast()
    return 

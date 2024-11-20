"""
{
  "NAME" : "network_consumer_demo",
  "TYPE" : "NetworkListener",
  
  "PATH_FILTER" : [
      null, null, 
      ["NET_LOOPBACK_DEMO", "NET_MON_01"],
      null
    ],
  "MESSAGE_FILTER" : {},
  
  "PLUGINS" : [
    {
      "SIGNATURE" : "NET_LOOPBACK_DEMO",
      "INSTANCES" : [
        {
          "INSTANCE_ID" : "NETWORK_CONSUMER_DEMO_INST1"
        }
      ]
    }
  ]
}

"""
from naeural_core.business.base import BasePluginExecutor as BasePlugin


__VER__ = '0.1.0'

_CONFIG = {
  
  **BasePlugin.CONFIG,
  'ALLOW_EMPTY_INPUTS' : True,
  
  'PROCESS_DELAY' : 0,
  
  'SEND_EACH' : 20,

  'VALIDATION_RULES' : {
    **BasePlugin.CONFIG['VALIDATION_RULES'],
  },
}

class NetLoopbackDemoPlugin(BasePlugin):
  
  
  def on_init(self):
    self.P("Network consumer loop-back demo initialized")
    self.__last_data_time = 0
    self.__data_id = 0
    return
  
  def __maybe_send(self):
    if self.time() - self.__last_data_time > self.cfg_send_each:
      self.__last_data_time = self.time()
      self.__data_id += 1
      self.P("Sending data with id: {}".format(self.__data_id))
      self.add_payload_by_fields(
        data_id=self.__data_id,
        data_json={
          "data_id_bis" : self.__data_id,
          "data" : "some data",
        }
      )
    return
  
  def __maybe_process_received(self):
    data = self.dataapi_struct_data()
    if data is not None:
      eeid = data.get('EE_ID', None)
      filtered_data = {
        k : v for k, v in data.items() if k in [
          'EE_SENDER', "DATA_ID", "DATA_JSON", "EE_TIMESTAMP", "SIGNATURE"
        ]
      }
      self.P("Received data from '{}':\n{}".format(eeid, self.json_dumps(filtered_data, indent=2)))
    return
    
  
  def process(self):
    payload = None
    self.__maybe_send()
    self.__maybe_process_received()    
    return payload
  

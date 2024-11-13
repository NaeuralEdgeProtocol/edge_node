"""
{
  "NAME" : "peer_config_demo",
  "TYPE" : "NetworkListener",
  
  "PATH_FILTER" : [
      null, null, 
      ["UPDATE_MONITOR_01", "NET_MON_01"],
      null
    ],
  "MESSAGE_FILTER" : {},
  
  "PLUGINS" : [
    {
      "SIGNATURE" : "NET_CONFIG_DEMO",
      "INSTANCES" : [
        {
          "INSTANCE_ID" : "NET_CONFIG_DEMO_INST1"
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
  
  'SEND_EACH' : 5,
  
  'VALIDATION_RULES' : {
    **BasePlugin.CONFIG['VALIDATION_RULES'],
  },
}

class PeerConfigDemoPlugin(BasePlugin):
  
  
  def on_init(self):
    self.P("Network peer config watch demo initializing...")
    self.__last_data_time = 0
    self.__allowed_nodes = {}
    return
  
  def __maybe_send(self):
    if self.time() - self.__last_data_time > self.cfg_send_each:
      self.P("I have {} pipelines locally. Sending requests to all nodes...".format(
        len(self.local_pipelines)
      ))
      self.__last_data_time = self.time()
      # now send some requests
      for node in self.__allowed_nodes:
        addr = node
        self.cmdapi_send_instance_command(
          pipeline="admin_pipeline",
          signature="UPDATE_MONITOR_01",
          instance_id="UPDATE_MONITOR_01_INST",
          instance_command="GET_PIPELINES",
          node_address=addr,
        )
    return
  
  def __maybe_process_received(self):
    data = self.dataapi_struct_data()
    if data is not None:
      eeid = data.get(self.const.PAYLOAD_DATA.EE_ID, None)
      sender = data.get(self.const.PAYLOAD_DATA.EE_SENDER, None)
      signature = data.get(self.const.PAYLOAD_DATA.SIGNATURE, None)
      is_encrypted = data.get(self.const.PAYLOAD_DATA.EE_IS_ENCRYPTED, False)
      self.P("Received {} '{}' data from '{}' <{}>".format(
        "encrypted" if is_encrypted else "unencrypted",
        signature, eeid, sender
      ))
      if signature == "NET_MON_01":        
        nodes_data = data.get("CURRENT_NETWORK")
        if nodes_data is not None:
          self.P("Received NET_MON_01 net-map data for {} nodes. Here is one of them:\n{}".format(
            len(nodes_data), nodes_data[list(nodes_data.keys())[0]]
          ))
          # get all whitelists
          # check if ee_addr in whitelist then add to allowed nodes
          # 
      elif signature == "UPDATE_MONITOR_01":
        self.P("Received UPDATE_MONITOR_01 data: \n{}".format(data))
      
    return
    
  
  def process(self):
    payload = None
    self.__maybe_send()
    self.__maybe_process_received()    
    return payload
  

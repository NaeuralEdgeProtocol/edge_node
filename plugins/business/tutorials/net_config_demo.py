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
  
  'MAX_INPUTS_QUEUE_SIZE' : 16,
  
  'PROCESS_DELAY' : 0,
  
  'SEND_EACH' : 10,
  
  'REQUEST_CONFIGS_EACH' : 30,
  
  'VALIDATION_RULES' : {
    **BasePlugin.CONFIG['VALIDATION_RULES'],
  },
}

class NetConfigDemoPlugin(BasePlugin):
  
  
  def on_init(self):
    self.P("Network peer config watch demo initializing...")
    self.__last_data_time = 0
    self.__new_nodes_this_iter = 0
    self.__allowed_nodes = {}
    return
  
  def __maybe_send(self):
    if self.time() - self.__last_data_time > self.cfg_send_each:
      self.__last_data_time = self.time()
      if len(self.__allowed_nodes) == 0:
        self.P("No allowed nodes to send requests to. Waiting for network data...")
      else:
        self.P("Initiating pipeline requests to allowed nodes...")
        to_send = []
        for node_addr in self.__allowed_nodes:
          last_request = self.__allowed_nodes[node_addr].get("last_config_get", 0)
          if (self.time() - last_request) > self.cfg_request_configs_each:
            to_send.append(node_addr)
          #endif enough time since last request of this node
        #endfor __allowed_nodes
        if len(to_send) == 0:
          self.P("No nodes need update.")
        else:
          self.P(f"Local {len(self.local_pipelines)} pipelines. Sending requests to {len(to_send)} nodes...")        
          # now send some requests
          for node_addr in to_send:
            node_ee_id = self.netmon.network_node_eeid(node_addr)
            self.P(f"Sending GET_PIPELINES to '{node_ee_id}' <{node_addr}>...")
            self.cmdapi_send_instance_command(
              pipeline="admin_pipeline",
              signature="UPDATE_MONITOR_01",
              instance_id="UPDATE_MONITOR_01_INST",
              instance_command={ "COMMAND": "GET_PIPELINES" },
              node_address=node_addr,
            )
            self.__allowed_nodes[node_addr]["last_config_get"] = self.time()
          #endfor to_send
        #endif len(to_send) == 0
      #endif have allowed nodes
    #endif time to send
    return
  
  def __maybe_process_received(self):
    data = self.dataapi_struct_data()
    if data is not None:
      payload_path = data.get(self.const.PAYLOAD_DATA.EE_PAYLOAD_PATH, [None, None, None, None])
      eeid = payload_path[0]
      signature = payload_path[2]
      sender = data.get(self.const.PAYLOAD_DATA.EE_SENDER, None)
      is_encrypted = data.get(self.const.PAYLOAD_DATA.EE_IS_ENCRYPTED, False)
      self.P("Received {}'{}' data from {}".format(
        "ENC " if is_encrypted else "",
        signature, f"'{eeid}' <{sender}>" if sender != self.ee_addr else "SELF",
      ))
      if signature == "NET_MON_01":        
        nodes_data = data.get("CURRENT_NETWORK")
        if nodes_data is None:
          self.P("Received NET_MON_01 data without CURRENT_NETWORK data.", color='r ')
        else:
          self.__new_nodes_this_iter = 0
          for node_data in nodes_data.values():
            addr = node_data.get("address", None)
            if addr == self.ee_addr:
              # its us, no need to check whitelist
              continue
            whitelist = node_data.get("whitelist", [])
            for ee_addr in whitelist:
              if ee_addr in self.ee_addr:
                # we have found a whitelist that contains our address
                if addr not in self.__allowed_nodes:
                  self.__allowed_nodes[addr] = {
                    "whitelist" : whitelist,
                    "last_config_get" : 0
                  } 
                  self.__new_nodes_this_iter += 1
                #endif not in allowed nodes
              #endif ee_addr in whitelist
            # endfor whitelist
          #endfor nodes_data
          if self.__new_nodes_this_iter > 0:
            self.P(f"Found {self.__new_nodes_this_iter} new nodes in the network that allow us to send commands.")
        #endif nodes_data is not None
      #endif signature == "NET_MON_01"
      
      elif signature == "UPDATE_MONITOR_01":        
        self.P("Received UPDATE_MONITOR_01 data: \n{}".format(
          self.json_dumps(data, indent=2)
        ))
        is_encrypted = data.get(self.const.PAYLOAD_DATA.EE_IS_ENCRYPTED, False)
        encrypted_data = data.get(self.const.PAYLOAD_DATA.EE_ENCRYPTED_DATA, None)
        if is_encrypted and encrypted_data is not None:
          self.P("Received encrypted data. Decrypting...")
          str_decrypted_data = self.bc.decrypt_str(
            str_b64data=encrypted_data,
            str_sender=sender,
          )
          decrypted_data = self.json_loads(str_decrypted_data)
          if decrypted_data is not None:
            received_pipelines = decrypted_data.get("EE_PIPELINES", [])
            self.P("Decrypted data size {} with pipelines:\n{}".format(
              len(str_decrypted_data),
              self.json_dumps(received_pipelines, indent=2),              
            ))
          else:
            self.P("Failed to decrypt data.", color='r')
          #endif decrypted_data is not None
        else:
          self.P("Received unencrypted data.")
        if sender in self.__allowed_nodes:
          #
          self.P(f"Updated last_config_get for node '{sender}'")
      #endif signature == "UPDATE_MONITOR_01"
      
    return
    
  
  def process(self):
    payload = None
    self.__maybe_send()
    self.__maybe_process_received()    
    return payload
  

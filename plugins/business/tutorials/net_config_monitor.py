"""
{
  "NAME" : "peer_config_pipeline",
  "TYPE" : "NetworkListener",
  
  "PATH_FILTER" : [
      null, null, 
      ["UPDATE_MONITOR_01", "NET_MON_01"],
      null
    ],
  "MESSAGE_FILTER" : {},
  
  "PLUGINS" : [
    {
      "SIGNATURE" : "NET_CONFIG_MONITOR",
      "INSTANCES" : [
        {
          "INSTANCE_ID" : "DEFAULT"
        }
      ]
    }
  ]
}

The full algoritm of this plugin is as follows:
1. At each iteration we check if data is avail from NET_MON_01.
2. If data is avail, we determine which nodes are allowed by which nodes from the list of active nodes.
3. For current node now I have the list of all nodes that allow me to connect to them.
4. At next iteration I will send COMMAND to UPDATE_MONITOR_01 for any required and allowed nodes.
5. If I receive data from UPDATE_MONITOR_01, I will *decrypt* it and update the list of pipelines for the sender node.

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
  
  'SHOW_EACH' : 60,
  
  'DEBUG_NETMON_COUNT' : 2,
  
  'VALIDATION_RULES' : {
    **BasePlugin.CONFIG['VALIDATION_RULES'],
  },
}

class NetConfigMonitorPlugin(BasePlugin):
  
  
  def on_init(self):
    self.P("Network peer config watch demo initializing...")
    self.__last_data_time = 0
    self.__new_nodes_this_iter = 0
    self.__last_shown = 0
    self.__allowed_nodes = {} # contains addresses with no prefixes
    self.__debug_netmon_count = self.cfg_debug_netmon_count
    return
  
  
  def __get_active_nodes(self, netmon_current_network : dict) -> dict:
    """
    Returns a dictionary with the active nodes in the network.
    """
    active_network = {
      v['address']: v 
      for k, v in netmon_current_network.items() 
      if v.get("working", False) == self.const.DEVICE_STATUS_ONLINE
    }    
    return active_network
  
  def __get_active_nodes_summary_with_peers(self, netmon_current_network: dict):
    """
    Looks in all whitelists and finds the nodes that is allowed by most other nodes.
    
    """
    node_coverage = {}
    
    active_network = self.__get_active_nodes(netmon_current_network)
    
    for addr in active_network:
      node_coverage[addr] = 0
    #endfor initialize node_coverage 
    
    whitelists = [x.get("whitelist", []) for x in active_network.values()]
    for whitelist in whitelists:
      for ee_addr in whitelist:
        if ee_addr not in active_network:
          continue # this address is not active in the network so we skip it
        if ee_addr not in node_coverage:
          node_coverage[ee_addr] = 0
        node_coverage[ee_addr] += 1
    coverage_list = [(k, v) for k, v in node_coverage.items()]
    coverage_list = sorted(coverage_list, key=lambda x: x[1], reverse=True)

    result = self.OrderedDict()
    my_addr = self.bc.maybe_remove_prefix(self.ee_addr)
    
    for i, (ee_addr, coverage) in enumerate(coverage_list):
      is_online = active_network.get(ee_addr, {}).get("working", False) == self.const.DEVICE_STATUS_ONLINE
      result[ee_addr] = {
        "peers" : coverage,
        "eeid" : active_network.get(ee_addr, {}).get("eeid", "UNKNOWN"),
        'ver'  : active_network.get(ee_addr, {}).get("version", "UNKNOWN"),
        'is_supervisor' : active_network.get(ee_addr, {}).get("is_supervisor", False),
        'allows_me' : my_addr in active_network.get(ee_addr, {}).get("whitelist", []),
        'online' : is_online,
        'whitelist' : active_network.get(ee_addr, {}).get("whitelist", []),
      }
    return result


  def __maybe_review_known(self):
    if ((self.time() - self.__last_shown) < self.cfg_show_each) or (len(self.__allowed_nodes) == 0):
      return
    self.__last_shown = self.time()
    msg = "Known nodes: "    
    for addr in self.__allowed_nodes:
      eeid = self.netmon.network_node_eeid(addr)
      pipelines = self.__allowed_nodes[addr].get("pipelines", [])
      names = [p.get("NAME", "NONAME") for p in pipelines]
      msg += f"\n  - '{eeid}' <{addr}> has {len(pipelines)} pipelines: {names}"
    #endfor __allowed_nodes
    self.P(msg)
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
      if sender == self.ee_addr:
        return
      if signature == "NET_MON_01":        
        current_network = data.get("CURRENT_NETWORK", {})
        if len(current_network) == 0:
          self.P("Received NET_MON_01 data without CURRENT_NETWORK data.", color='r ')
        else:
          self.__new_nodes_this_iter = 0
          peers_status = self.__get_active_nodes_summary_with_peers(current_network)
          if self.__debug_netmon_count > 0:
            # self.P(f"NetMon debug:\n{self.json_dumps(self.__get_active_nodes(current_network), indent=2)}")
            self.P(f"Peers status:\n{self.json_dumps(peers_status, indent=2)}")
            self.__debug_netmon_count -= 1
          for addr in peers_status:
            if addr == self.ee_addr:
              # its us, no need to check whitelist
              continue
            if peers_status[addr]["allows_me"]:
              # we have found a whitelist that contains our address
              if addr not in self.__allowed_nodes:
                self.__allowed_nodes[addr] = {
                  "whitelist" : peers_status[addr]["whitelist"],
                  "last_config_get" : 0
                } 
                self.__new_nodes_this_iter += 1
              #endif addr not in __allowed_nodes
            #endif addr allows me
          #endfor each addr in peers_status
          if self.__new_nodes_this_iter > 0:
            self.P(f"Found {self.__new_nodes_this_iter} new peered nodes.")
        #endif nodes_data is not None
      #endif signature == "NET_MON_01"
      
      elif signature == "UPDATE_MONITOR_01":        
        is_encrypted = data.get(self.const.PAYLOAD_DATA.EE_IS_ENCRYPTED, False)
        encrypted_data = data.get(self.const.PAYLOAD_DATA.EE_ENCRYPTED_DATA, None)
        if is_encrypted and encrypted_data is not None:
          self.P("Received UPDATE_MONITOR_01 encrypted data. Decrypting...")
          str_decrypted_data = self.bc.decrypt_str(
            str_b64data=encrypted_data,
            str_sender=sender,
          )
          decrypted_data = self.json_loads(str_decrypted_data)
          if decrypted_data is not None:
            received_pipelines = decrypted_data.get("EE_PIPELINES", [])
            self.P("Decrypted data size {} with {} pipelines:\n{}".format(
              len(str_decrypted_data), len(received_pipelines),
              self.json_dumps([
                {
                  k:v for k,v in x.items() 
                  if k in ["NAME", "TYPE", "MODIFIED_BY_ADDR", "LAST_UPDATE_TIME"]
                } 
                for x in received_pipelines], 
                indent=2),
            ))
            sender_no_prefix = self.bc.maybe_remove_prefix(sender)
            self.__allowed_nodes[sender_no_prefix]["pipelines"] = received_pipelines
            # now we can add the pipelines to the netmon cache
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
    self.__maybe_review_known()  
    return payload
  

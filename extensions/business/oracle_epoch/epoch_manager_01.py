"""

The EpochManager01Plugin is a FastAPI web app that provides endpoints to interact with the
oracle network of the Naeural Edge Protocol

Each request will generate data as follows:
- availablity data is requested from the oracle API
- the data is signed with EVM signature and signature/address is added
- other oracle peers signatures are added - all must be on same agreed availability
- package is node-signed and returned to the client

"""

from naeural_core.business.default.web_app.supervisor_fast_api_web_app import SupervisorFastApiWebApp as BasePlugin

__VER__ = '0.3.2'

_CONFIG = {
  **BasePlugin.CONFIG,

  'PORT': None,
  # 'ASSETS': 'plugins/business/fastapi/epoch_manager',
  'VALIDATION_RULES': {
    **BasePlugin.CONFIG['VALIDATION_RULES'],
  },
}


class EpochManager01Plugin(BasePlugin):
  """
  This plugin is a FastAPI web app that provides endpoints to interact with the
  EpochManager of the Neural Core.
  """
  CONFIG = _CONFIG

  def __init__(self, **kwargs):
    super(EpochManager01Plugin, self).__init__(**kwargs)
    return


  def on_init(self):
    super(EpochManager01Plugin, self).on_init()
    my_address = self.bc.address
    current_epoch = self.__get_current_epoch()
    start_epoch = current_epoch - 6
    end_epoch = current_epoch - 1
    if start_epoch < 1:
      start_epoch = 1
    if end_epoch < 1:
      end_epoch = 1
    my_node_info = self.__get_node_epochs(
      my_address, 
      start_epoch=start_epoch, end_epoch=end_epoch
    )
    self.P("Started {} plugin in epoch {}. Local node info:\n{}".format(
      self.__class__.__name__, current_epoch, self.json_dumps(my_node_info, indent=2))
    )
    return


  def __sign(self, data):
    """
    Sign the given data using the blockchain engine.
    Returns the signature. 
    Use the data param as it will be modified in place.
    """
    signature = self.bc.sign(data, add_data=True, use_digest=True)
    return signature


  def __get_response(self, dct_data: dict):
    """
    Create a response dictionary with the given data.

    Parameters
    ----------
    dct_data : dict
        The data to include in the response - data already prepared 

    Returns
    -------
    dict
        The input dictionary with the following keys added:
        - server_alias: str
            The literal alias of the current node.

        - server_time: str
            The current time in UTC of the current node.

        - server_current_epoch: int
            The current epoch of the current node.

        - server_uptime: str
            The time that the current node has been running.
    """
    str_utc_date = self.datetime.now(self.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    # dct_data['server_id'] = self.node_addr # redundant due to the EE_SENDER
    dct_data['server_alias'] = self.node_id
    dct_data['server_version'] = self.ee_ver
    dct_data['server_time'] = str_utc_date
    dct_data['server_current_epoch'] = self.__get_current_epoch()
    dct_data['server_uptime'] = str(self.timedelta(seconds=int(self.time_alive)))
    self.__sign(dct_data) # add the signature over full data
    return dct_data

  def __get_current_epoch(self):
    """
    Get the current epoch of the node.

    Returns
    -------
    int
        The current epoch of the node.
    """
    return self.netmon.epoch_manager.get_current_epoch()
  
  
  def __eth_to_internal(self, eth_node_address):
    return self.netmon.epoch_manager.eth_to_internal(eth_node_address)
  
  
  def __get_signed_data(self, node_addr : str, epochs : list, epochs_vals : list):
    """    
    Sign the given data using the blockchain engine.
    Returns the signature. 
    Use the data param as it will be modified in place.
    
    Parameters
    ----------
    
    node_addr: str
      The internal node address (not EVM)
    
    """
    node_addr_eth = self.bc.node_address_to_eth_address(node_addr)
    res = self.bc.eth_sign_node_epochs(
      node=node_addr_eth, 
      epochs=epochs,
      epochs_vals=epochs_vals, 
      signature_only=False,
    )
    eth_signature = res["signature"]
    inputs = res["eth_signed_data"]
    eth_signatures = [eth_signature]
    eth_addresses = [self.bc.eth_address]
    # now add oracle peers signatures and addresses

    data = {
      'node': node_addr,
      'node_eth_address': node_addr_eth,
      'epochs': epochs,
      'epochs_vals': epochs_vals,
      
      'eth_signed_data' : {
        "input" : inputs,
        "signature_field" : "eth_signature",        
      },
      
      'eth_signatures': eth_signatures, 
      'eth_addresses': eth_addresses, 
    }    
    return data
  
  
  def __get_node_epochs(self, node_addr: str, start_epoch: int = 1, end_epoch: int = None):
    """
    Get the epochs availabilities for a given node.

    Parameters
    ----------
    node_addr : str
        The internal address of a node.
        
    start_epoch : int
        The first epoch to get the availability for.
        
    end_epoch : int
        The last epoch to get the availability for.

    Returns
    -------
      dict
        A dictionary with the following keys
        - node: str
            The address of the node.
        - epochs_vals: list
            A list of integers, each integer is the epoch value for the node.
        - eth_signature: str  
            The EVM signature of the data.
        - eth_address: str
            The address of the EVM account used to sign the data.
            

    """
    error_msg = None
    if end_epoch is None:
      end_epoch = self.__get_current_epoch() - 1
    if node_addr is None:
      error_msg = "Node address is None"
    if not isinstance(node_addr, str):
      error_msg = "Node address is not a string"
    if isinstance(start_epoch, str):
      start_epoch = int(start_epoch)
    if isinstance(end_epoch, str):
      end_epoch = int(end_epoch)
    if not isinstance(start_epoch, int):
      error_msg = "Start epoch is not an integer"
    if not isinstance(end_epoch, int):
      error_msg = "End epoch is not an integer"
    if start_epoch > end_epoch:
      error_msg = "Start epoch is greater than end epoch"
    if end_epoch < 1:
      error_msg = "End epoch is less than 1"
    if end_epoch >= self.__get_current_epoch():
      error_msg = "End epoch is greater or equal than the current epoch"
    
    if error_msg is not None:
      data = {
        'node': node_addr,
        'error': error_msg,
      }
    else:
      self.P(f"Getting epochs for node {node_addr} from {start_epoch} to {end_epoch}")
      epochs_vals = self.netmon.epoch_manager.get_node_epochs(
        node_addr, 
        autocomplete=True,
        as_list=False
      )    
      if epochs_vals is None:
        data = {
          'node': node_addr,
          'error': "No epochs found for the node",
        }
      else:
        epochs = list(range(start_epoch, end_epoch + 1)) 
        epochs_vals_selected = [epochs_vals[x] for x in epochs]
        data = self.__get_signed_data(node_addr, epochs, epochs_vals_selected)
        # now add the certainty for each requested epoch
        data["oracle"] = self.netmon.epoch_manager.get_oracle_state()
        
    #endif
    return data

  # List of endpoints, these are basically wrappers around the netmon
  # epoch manager.

  @BasePlugin.endpoint
  # /nodes_list
  def nodes_list(self):
    """
    Returns the list of all known nodes in the network - both online and offline.
    The known nodes are nodes that sent at least one heartbeat while the current node was running.

    Returns
    -------
    dict
        A dictionary with the following keys:
        - nodes: list
            A list of strings, each string is the address of a node in the network.

        - server_id: str
            The address of the responding node.

        - server_time: str
            The current time in UTC of the responding node.

        - server_current_epoch: int
            The current epoch of the responding node.

        - server_uptime: str
            The time that the responding node has been running.
    """
    # nodes = self.netmon.epoch_manager.get_node_list()
    # nodes = {
    #   x : {
    #     "alias" :  self.netmon.network_node_eeid(addr=x),
    #     "eth_address" : self.bc.node_address_to_eth_address(x),
    #   } for x in nodes 
    # }    
    nodes = self.netmon.epoch_manager.get_stats(display=True, online_only=False)
    response = self.__get_response({
      'nodes': nodes,
    })
    return response
  

  @BasePlugin.endpoint
  # /active_nodes_list
  def active_nodes_list(self):
    """
    Returns the list of known and currently active nodes in the network.
    For all the nodes use the `nodes_list` endpoint.

    Returns
    -------
    dict
        A dictionary with the following keys:
        - nodes: list
            A list of strings, each string is the address of a node in the network.

        - server_id: str
            The address of the responding node.

        - server_time: str
            The current time in UTC of the responding node.

        - server_current_epoch: int
            The current epoch of the responding node.

        - server_uptime: str
            The time that the responding node has been running.
    """
    # nodes = self.netmon.epoch_manager.get_node_list()
    # nodes = {
    #   x : {
    #     "alias" :  self.netmon.network_node_eeid(addr=x),
    #     "eth_address" : self.bc.node_address_to_eth_address(x),        
    #   } for x in nodes 
    #   if self.netmon.network_node_simple_status(addr=x) == self.const.DEVICE_STATUS_ONLINE
    # }
    nodes = self.netmon.epoch_manager.get_stats(display=True, online_only=True)
    response = self.__get_response({
      'nodes': nodes,
    })
    return response
  
  
  @BasePlugin.endpoint
  def node_epochs_range(self, eth_node_addr : str, start_epoch : int, end_epoch : int):
    """
    Returns the list of epochs availabilities for a given node in a given range of epochs.

    Parameters
    ----------
    eth_node_addr : str
        The address of a node.
        
    start_epoch : int
        The first epoch of the range.
        
    end_epoch : int
        The last epoch of the range.

    Returns
    -------
    dict
        A dictionary with the following keys:
        - node: str
            The address of the node.

        - epochs_vals: list
            A list of integers, each integer is the epoch value for the node.

        - server_id: str
            The address of the responding node.

        - server_time: str
            The current time in UTC of the responding node.

        - server_current_epoch: int
            The current epoch of the responding node.

        - server_uptime: str
            The time that the responding node has been running.
    """  
    node_addr = self.__eth_to_internal(eth_node_addr)    
    
    response = self.__get_response(self.__get_node_epochs(
      node_addr, start_epoch=start_epoch, end_epoch=end_epoch
    ))
    return response

  @BasePlugin.endpoint
  # /node_epochs
  def node_epochs(self, eth_node_addr: str):
    """
    Returns the list of epochs availabilities for a given node.

    Parameters
    ----------
    eth_node_addr : str
        The EVM address of a node.

    Returns
    -------
    dict

    """
    node_addr = self.__eth_to_internal(eth_node_addr)    
    if node_addr is None:
      return None
    if not isinstance(node_addr, str):
      return None

    response = self.__get_response(self.__get_node_epochs(node_addr))
    return response

  @BasePlugin.endpoint
  # /node_epoch
  def node_epoch(self, eth_node_addr: str, epoch: int):
    """
    Returns the availability of a given node in a given epoch.

    Parameters
    ----------
    eth_node_addr : str
        The EVM address of a node.
        
    epoch : int
        The target epoch.

    Returns
    -------
    dict
        A dictionary with the following keys:
        - node: str
            The address of the node.

        - epoch_id: int
            The target epoch.

        - epoch_val: int
            The availability score of the node in the epoch (between 0 and 255).

        - epoch_prc: float
            The availability score of the node in the epoch as a percentage (between 0 and 1).
    """
    node_addr = self.__eth_to_internal(eth_node_addr)    
    data = self.__get_node_epochs(node_addr, start_epoch=epoch, end_epoch=epoch)
    if isinstance(data.get('epochs_vals'), list) and len(data['epochs_vals']) > 0:
      epoch_val = data['epochs_vals'][0]
      epoch_val_direct = self.netmon.epoch_manager.get_node_epoch(node_addr, epoch)
      assert epoch_val == epoch_val_direct
      response = self.__get_response({
        'epoch_id': epoch,
        'epoch_val': epoch_val,
        'epoch_prc': round(epoch_val / 255, 4),
        **data
      })
    else:
      response = self.__get_response({
        **data
      })
    return response

  @BasePlugin.endpoint
  # /node_last_epoch
  def node_last_epoch(self, eth_node_addr: str):
    """
    Returns the availability of a given node in the last epoch.

    Parameters
    ----------
    eth_node_addr : str
        The EVM address of a node.

    Returns
    -------
    dict
        A dictionary with the following keys:
        - node: str
            The address of the node.

        - last_epoch_id: int
            The last epoch.

        - last_epoch_val: int
            The availability score of the node in the last epoch (between 0 and 255).

        - last_epoch_prc: float
            The availability score of the node in the last epoch as a percentage (between 0 and 1).

    """
    node_addr = self.__eth_to_internal(eth_node_addr)
    epoch = self.__get_current_epoch() - 1
    data = self.__get_node_epochs(node_addr, start_epoch=epoch, end_epoch=epoch)
    if isinstance(data.get('epochs_vals'), list) and len(data['epochs_vals']) > 0:
      epoch_val = data['epochs_vals'][0]
      epoch_val_direct = self.netmon.epoch_manager.get_node_epoch(node_addr, epoch)
      assert epoch_val == epoch_val_direct
      response = self.__get_response({
        'last_epoch_id': epoch,
        'last_epoch_val': epoch_val,
        'last_epoch_prc': round(epoch_val / 255, 4),
        **data
      })
    else:
      response = self.__get_response({
        **data
      })
    return response

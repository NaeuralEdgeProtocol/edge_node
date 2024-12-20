from extensions.business.fastapi.supervisor_fast_api_web_app import SupervisorFastApiWebApp as BasePlugin

__VER__ = '0.2.1'

_CONFIG = {
  **BasePlugin.CONFIG,

  'PORT': None,
  'ASSETS': 'plugins/business/fastapi/epoch_manager',
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
    my_node_info = self.__get_node_epochs(my_address)
    self.P("Started {} plugin. Local node info:\n{}".format(
      self.__class__.__name__, self.json_dumps(my_node_info))
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
  
  
  def __get_signed_data(self, node_addr : str, epochs : list, epochs_vals : list):
    """
    Sign the given data using the blockchain engine.
    Returns the signature. 
    Use the data param as it will be modified in place.
    """

    eth_signature = self.bc.eth_sign_node_epochs(
      node=node_addr, 
      epochs=epochs,
      epochs_vals=epochs_vals, 
      signature_only=True,
    )
    eth_address = self.bc.eth_address

    data = {
      'node': node_addr,
      'node_eth_address': self.bc.node_address_to_eth_address(node_addr),
      'epochs': epochs,
      'epochs_vals': epochs_vals,
      
      'eth_signed_data' : {
        "input" : ["node(string)", "epochs(uint256[])", "epochs_vals(uint256[])"],
        "signature_field" : "eth_signature",        
      },
      'eth_signature': eth_signature, 
      'eth_address': eth_address, # this is actually obsolete as it is already provided by "EE_ETH_SENDER"
    }    
    return data
  
  
  def __get_node_epochs(self, node_addr: str, start_epoch: int = 1, end_epoch: int = None):
    """
    Get the epochs availabilities for a given node.

    Parameters
    ----------
    node_addr : str
        The address of a node.
        
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
    #endif
    return data

  # List of endpoints, these are basically wrappers around the netmon
  # epoch manager.

  @BasePlugin.endpoint
  # /nodes_list
  def nodes_list(self):
    """
    Returns the list of known nodes in the network.
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
    nodes = self.netmon.epoch_manager.get_node_list()
    nodes = {
      x : {
        "alias" :  self.netmon.network_node_eeid(addr=x),
        "eth_address" : self.bc.node_address_to_eth_address(x),
      } for x in nodes 
    }    
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
    nodes = self.netmon.epoch_manager.get_node_list()
    nodes = {
      x : {
        "alias" :  self.netmon.network_node_eeid(addr=x),
        "eth_address" : self.bc.node_address_to_eth_address(x),        
      } for x in nodes 
      if self.netmon.network_node_simple_status(addr=x) == self.const.DEVICE_STATUS_ONLINE
    }
    response = self.__get_response({
      'nodes': nodes,
    })
    return response
  
  
  @BasePlugin.endpoint
  def node_epochs_range(self, node_addr : str, start_epoch : int, end_epoch : int):
    """
    Returns the list of epochs availabilities for a given node in a given range of epochs.

    Parameters
    ----------
    node_addr : str
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
    response = self.__get_response(self.__get_node_epochs(
      node_addr, start_epoch=start_epoch, end_epoch=end_epoch
    ))
    return response

  @BasePlugin.endpoint
  # /node_epochs
  def node_epochs(self, node_addr: str):
    """
    Returns the list of epochs availabilities for a given node.

    Parameters
    ----------
    node_addr : str
        The address of a node.

    Returns
    -------
    dict

    """
    if node_addr is None:
      return None
    if not isinstance(node_addr, str):
      return None

    response = self.__get_response(self.__get_node_epochs(node_addr))
    return response

  @BasePlugin.endpoint
  # /node_epoch
  def node_epoch(self, node_addr: str, epoch: int):
    """
    Returns the availability of a given node in a given epoch.

    Parameters
    ----------
    node_addr : str
        The address of a node.
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
  def node_last_epoch(self, node_addr: str):
    """
    Returns the availability of a given node in the last epoch.

    Parameters
    ----------
    node_addr : str
        The address of a node.

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

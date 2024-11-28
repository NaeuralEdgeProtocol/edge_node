from naeural_core.business.default.web_app.fast_api_web_app import FastApiWebAppPlugin

__VER__ = '0.1.0.0'

_CONFIG = {
  **FastApiWebAppPlugin.CONFIG,
  'USE_NGROK': False,
  'NGROK_ENABLED': False,
  'NGROK_DOMAIN': None,
  'NGROK_EDGE_LABEL': None,

  'PORT': None,
  'ASSETS': 'plugins/business/fastapi/epoch_manager',
  'VALIDATION_RULES': {
    **FastApiWebAppPlugin.CONFIG['VALIDATION_RULES'],
  },
}


class EpochManager01Plugin(FastApiWebAppPlugin):
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
      self.__class__.__name__, self.json_dumps(my_node_info, indent=2))
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
    dct_data['server_alias'] - self.node_id
    dct_data['server_version'] = self.ee_ver
    dct_data['server_time'] = str_utc_date
    dct_data['server_current_epoch'] = self.__get_current_epoch()
    # TODO: make in the format "84 days, 8:47:51"
    dct_data['server_uptime'] = str(self.timedelta(seconds=int(self.time_alive)))
    self.__sign(dct_data)
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
      'epochs': epochs,
      'epochs_vals': epochs_vals,
      
      'eth_signed_data' : ["node(string)", "epochs(uint256[])", "epochs_vals(uint256[])"],
      'eth_signature': eth_signature,
      'eth_address': eth_address,
    }    
    return data
  
  
  def __get_node_epochs(self, node_addr: str):
    """
    Get the epochs availabilities for a given node.

    Parameters
    ----------
    node_addr : str
        The address of a node.

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
    epochs_vals = self.netmon.epoch_manager.get_node_epochs(
      node_addr, 
      autocomplete=True,
      as_list=True
    )    
    epochs = list(range(1, len(epochs_vals) + 1))
    
    data = self.__get_signed_data(node_addr, epochs, epochs_vals)
    return data

  # List of endpoints, these are basically wrappers around the netmon
  # epoch manager.

  @FastApiWebAppPlugin.endpoint
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
    response = self.__get_response({
      'nodes': nodes,
    })
    return response

  @FastApiWebAppPlugin.endpoint
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
    if node_addr is None:
      return None
    if not isinstance(node_addr, str):
      return None

    response = self.__get_response(self.__get_node_epochs(node_addr))
    return response

  @FastApiWebAppPlugin.endpoint
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

        - server_id: str
            The address of the responding node.

        - server_time: str
            The current time in UTC of the responding node.

        - server_current_epoch: int
            The current epoch of the responding node.

        - server_uptime: str
            The time that the responding node has been running.
    """
    if node_addr is None or epoch is None:
      return None
    if not isinstance(node_addr, str):
      return None
    if isinstance(epoch, str):
      epoch = int(epoch)
    if not isinstance(epoch, int):
      return None
    epoch_val = self.netmon.epoch_manager.get_node_epoch(node_addr, epoch)
    
    epochs = [epoch]
    epochs_vals = [epoch_val]

    data = self.__get_signed_data(node_addr, epochs, epochs_vals)

    response = self.__get_response({
      'epoch_id': epoch,
      'epoch_val': epoch_val,
      'epoch_prc': round(epoch_val / 255, 4),
      **data
    })
    return response

  @FastApiWebAppPlugin.endpoint
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

        - server_id: str
            The address of the responding node.

        - server_time: str
            The current time in UTC of the responding node.

        - server_current_epoch: int
            The current epoch of the responding node.

        - server_uptime: str
            The time that the responding node has been running.
    """
    if node_addr is None:
      return None
    if not isinstance(node_addr, str):
      return None
    last_epoch_val = self.netmon.epoch_manager.get_node_last_epoch(node_addr)
    last_epoch = self.__get_current_epoch() - 1
    
    epochs = [last_epoch]
    epochs_vals = [last_epoch_val]
    data = self.__get_signed_data(node_addr, epochs, epochs_vals)

    response = self.__get_response({
      'last_epoch_id': last_epoch,
      'last_epoch_val': last_epoch_val,
      'last_epoch_prc': round(last_epoch_val / 255, 4),
      **data,
    })
    return response

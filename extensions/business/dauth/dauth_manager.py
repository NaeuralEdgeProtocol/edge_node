"""

EE_HB_CONTAINS_PIPELINES=0
EE_HB_CONTAINS_ACTIVE_PLUGINS=1
EE_EPOCH_MANAGER_DEBUG=1
WHITELIST (oracles)




"""

from naeural_core.business.default.web_app.supervisor_fast_api_web_app import SupervisorFastApiWebApp as BasePlugin
from naeural_client.bc import DefaultBlockEngine

__VER__ = '0.2.2'

_CONFIG = {
  **BasePlugin.CONFIG,

  'PORT': None,
  
  'ASSETS' : 'nothing', # TODO: this should not be required in future
  
  'DAUTH_VERBOSE' : True,
  
  # required ENV keys are defined in plugin template and should be added here
  
  "AUTH_ENV_KEYS" : [
  ],
  
  "AUTH_PREDEFINED_KEYS" : {
  },
  
  'VALIDATION_RULES': {
    **BasePlugin.CONFIG['VALIDATION_RULES'],
  },
}

def version_to_int(version):
  """
  Convert a version string to an integer.
  """
  val = 0
  try:
    parts = version.strip().split('.')
    for i, part in enumerate(reversed(parts)):
      val += int(part) * (1000 ** i)
  except:
    pass
  return val

class DauthManagerPlugin(BasePlugin):
  """
  This plugin is the dAuth FastAPI web app that provides an endpoints for decentralized authentication.
  """
  CONFIG = _CONFIG

  def __init__(self, **kwargs):
    super(DauthManagerPlugin, self).__init__(**kwargs)
    return
  
  
  def Pd(self, *args, **kwargs):
    """
    Print a message to the console.
    """
    if self.cfg_dauth_verbose:
      self.P(*args, **kwargs)
    return  

  def on_init(self):
    super(DauthManagerPlugin, self).on_init()
    my_address = self.bc.address
    my_eth_address = self.bc.eth_address
    self.P("Started {} plugin on {} / {}\n - Auth keys: {}\n - Predefined keys: {}".format(
      self.__class__.__name__, my_address, my_eth_address,
      self.cfg_auth_env_keys, self.cfg_auth_predefined_keys)
    )
    return
  
  @property
  def __bc(self) -> DefaultBlockEngine:
    return self.global_shmem[self.const.BLOCKCHAIN_MANAGER]
  
  
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
  
  def get_whitelist_data(self):
    """
    Get the whitelist data for the current node.
    """
    lst_data = None
    try:
      wl, names = self.__bc.whitelist_with_names
      lst_data = [a + (f"  {b}" if len(b) > 0 else "") for a, b in zip(wl, names)]
    except Exception as e:
      self.P("Error getting whitelist data: {}".format(e), color='r')      
    return lst_data

  
  
  def version_check(self, data):
    """
    Check the version of the node that is sending the request.
    Returns `None` if all ok and a message if there is a problem.
    """
    dAuthCt = self.const.BASE_CT.dAuth
    sender_app_version = data.get(dAuthCt.DAUTH_SENDER_APP_VER)
    sender_core_version = data.get(dAuthCt.DAUTH_SENDER_CORE_VER)
    sender_sdk_version = data.get(dAuthCt.DAUTH_SENDER_SDK_VER)
    int_sender_app_version = version_to_int(sender_app_version)
    int_sender_core_version = version_to_int(sender_core_version)
    int_sender_sdk_version = version_to_int(sender_sdk_version)
    int_server_version = version_to_int(self.ee_ver)
    return None
  
  def check_if_node_allowed(self, node_address):
    """
    Check if the node address is allowed to request authentication data.
    """
    return True
  
  
  def chainstore_store_dauth_request(self, requester, dauth_data):
    """
    Set the chainstore data for the requester.
    """
    return
  
  

  @BasePlugin.endpoint(method="post")
  # /get_auth_data
  def get_auth_data(self, body: dict):
    """
    Receive a request for authentication data from a node and return the data if the request is valid.

    Parameters
    ----------
    {
      "body" : {
        "EE_SENDER" : "sender node address",
        "EE_SIGN" : "sender signature on the message",
        "EE_HASH" : "message hash",
        "nonce" : "some-nonce"
        ... other data
      }      
    }
    
    """
    
    lst_auth_env_keys = self.cfg_auth_env_keys
    dct_auth_predefined_keys = self.cfg_auth_predefined_keys
    
    DAUTH_SUBKEY = self.const.BASE_CT.DAUTH_SUBKEY
    dAuthCt = self.const.BASE_CT.dAuth
    data = {
      DAUTH_SUBKEY : {
        'error' : None,
      },
    }
    error = None
    requester = body.get(self.const.BASE_CT.BCctbase.SENDER)
        
    self.Pd("Received request from {} for auth:\n{}".format(
      requester, self.json_dumps(body, indent=2))
    )
    
    ###### verify the request signature ######
    verify_data = self.bc.verify(body, return_full_info=True)
    if not verify_data.valid:
      error = 'Invalid request signature: {}'.format(verify_data.message)

    ###### basic version checks ######
    version_check = self.version_check(body)
    if version_check is None:
      error = 'Version check failed: {}'.format(version_check)

    ###### check if node_address is allowed ######   
    allowed_to_dauth = self.check_if_node_allowed(requester)   
    if not allowed_to_dauth:
      error = 'Node not allowed to request auth data.'      
    
    if error is not None:
      data[DAUTH_SUBKEY]['error'] = error
      self.Pd("Error on request from {}: {}".format(requester, error), color='r')
    else:
      ### get the whitelist and populate answer  ###      
      data[DAUTH_SUBKEY][dAuthCt.DAUTH_WHITELIST] = self.get_whitelist_data()

      #####  finally prepare the env auth data #####
      for key in lst_auth_env_keys:
        if key.startswith(dAuthCt.DAUTH_ENV_KEYS_PREFIX):
          data[DAUTH_SUBKEY][key] = self.os_environ.get(key)
      
      # overwrite the predefined keys
      for key in dct_auth_predefined_keys:
        data[DAUTH_SUBKEY][key] = dct_auth_predefined_keys[key]
              
      # record the node_address and the auth data      
      self.chainstore_store_dauth_request(
        requester=requester, dauth_data=data
      )
    #end no errors
    
    if self.cfg_dauth_verbose:
      data['request'] = body
    
    response = self.__get_response({
      **data
    })
    return response

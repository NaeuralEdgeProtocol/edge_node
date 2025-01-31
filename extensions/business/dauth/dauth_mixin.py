def version_to_int(version):
  """
  Convert a version string to an integer.
  """
  val = 0
  if version is not None:
    try:
      parts = version.strip().split('.')
      for i, part in enumerate(reversed(parts)):
        val += int(part) * (1000 ** i)
    except:
      pass
  return val

class _DotDict(dict):
  __getattr__ = dict.__getitem__
  __setattr__ = dict.__setitem__
  __delattr__ = dict.__delitem__
  
  
class VersionCheckData(_DotDict):
  """
  Data class for version check.
  """
  def __init__(self, result, message):
    self.result = result
    self.message = message
    self.requester_type = None
    return

class _DauthMixin:
  const = None

  def Pd(self, *args, **kwargs):
    """
    Print a message to the console.
    """
    if self.cfg_dauth_verbose:
      self.P(*args, **kwargs)
    return  

  def __eth_to_internal(self, eth_node_address):
    return self.netmon.epoch_manager.eth_to_internal(eth_node_address)
  

  def __internal_to_eth(self, internal_node_address):
    return self.bc_direct.node_address_to_eth_address(internal_node_address)
  
  
  def _eth_list_to_internal(self, lst_eth):
    return [self.__eth_to_internal(eth) for eth in lst_eth]

 
  def get_whitelist_data(self):
    """
    Get the whitelist data for the current node.
    """
    lst_data = None
    try:
      wl, names = self.bc_direct.whitelist_with_names
      lst_data = [a + (f"  {b}" if len(b) > 0 else "") for a, b in zip(wl, names)]
    except Exception as e:
      self.P("Error getting whitelist data: {}".format(e), color='r')      
    return lst_data
  
  
  def get_mandatory_oracles(self):
    """
    Get the list of oracles that must be allowed.
    """
    mandatory_oracles = []
    try:
      # TODO: modify this to Web3 approach
      mandatory_oracles = self.get_whitelist_data()
    except Exception as e:
      self.P("Error getting mandatory oracles: {}".format(e), color='r')
    return mandatory_oracles
      

  
  
  def version_check(self, data : dict):
    """
    Check the version of the node that is sending the request.
    Returns `None` if all ok and a message if there is a problem.
    
    
    """    
    #
    output = VersionCheckData(result=True, message="")
    dAuthCt = self.const.BASE_CT.dAuth
    sender_app_version = data.get(dAuthCt.DAUTH_SENDER_APP_VER)
    sender_core_version = data.get(dAuthCt.DAUTH_SENDER_CORE_VER)
    sender_sdk_version = data.get(dAuthCt.DAUTH_SENDER_SDK_VER)
    int_sender_app_version = version_to_int(sender_app_version)
    int_sender_core_version = version_to_int(sender_core_version)
    int_sender_sdk_version = version_to_int(sender_sdk_version)
    int_server_app_version = version_to_int(self.ee_ver)
    int_server_core_version = version_to_int(self.ee_core_ver)
    int_server_sdk_version = version_to_int(self.ee_sdk_ver)
    
    if int_sender_app_version == 0 and int_sender_core_version == 0 and int_sender_sdk_version > 0:
      output.requester_type = dAuthCt.DAUTH_SENDER_TYPE_SDK
    elif int_sender_app_version == 0 and int_sender_core_version >0 and int_sender_sdk_version > 0:
      output.requester_type = dAuthCt.DAUTH_SENDER_TYPE_CORE
      output.result = False # we should block this
    elif int_sender_app_version > 0 and int_sender_core_version > 0 and int_sender_sdk_version > 0:
      output.requester_type = dAuthCt.DAUTH_SENDER_TYPE_NODE
    else:
      output.requester_type = "unknown"
      output.result = False
      output.message = "Invalid sender version data."
    
    if int_sender_app_version > 0 and int_sender_app_version < int_server_app_version:
      output.message += f" Sender app version {sender_app_version} is lower than server app version {self.ee_ver}."
      # maybe we should block below a certain level
    if int_sender_core_version > 0 and int_sender_core_version < int_server_core_version:
      output.message += f" Sender core version {sender_core_version} is lower than server core version {self.ee_core_ver}."
      # maybe we should block below a certain level
    if int_sender_sdk_version > 0 and int_sender_sdk_version < int_server_sdk_version:
      output.message += f" Sender sdk version {sender_sdk_version} is lower than server sdk version {self.ee_sdk_ver}."
      # maybe we should block below a certain level
    return output
  
  def check_if_node_allowed(
    self, 
    node_address : str, 
    node_address_eth : str, 
    version_check_data : VersionCheckData
  ):
    """
    Check if the node address is allowed to request authentication data.
    """
    result = True
    if not version_check_data.result:
      result = False
    else:
      pass
    return result
  
  
  def chainstore_store_dauth_request(
    self, 
    node_address : str, 
    node_address_eth : str, 
    dauth_data : dict
  ):
    """
    Set the chainstore data for the requester.
    
    
    """
    self.Pd("CSTORE dAuth data for node {} ({})".format(node_address, node_address_eth))
    return
  
  
  def fill_dauth_data(self, dauth_data):
    """
    Fill the data with the authentication data.
    """
    dAuthCt = self.const.BASE_CT.dAuth

    lst_auth_env_keys = self.cfg_auth_env_keys
    dct_auth_predefined_keys = self.cfg_auth_predefined_keys
    
    ### get the mandatory oracles whitelist and populate answer  ###      
    dauth_data[dAuthCt.DAUTH_WHITELIST] = self.get_mandatory_oracles()

    #####  finally prepare the env auth data #####
    for key in lst_auth_env_keys:
      if key.startswith(dAuthCt.DAUTH_ENV_KEYS_PREFIX):
        dauth_data[key] = self.os_environ.get(key)
    
    # overwrite the predefined keys
    for key in dct_auth_predefined_keys:
      dauth_data[key] = dct_auth_predefined_keys[key]

    return dauth_data
  
  
  def fill_extra_info(
    self, 
    data : dict, 
    sender_eth_address : str, 
    body : dict,
    version_check_data : VersionCheckData
  ):
    """
    Fill the data with the extra information.
    """
    dAuthConst = self.const.BASE_CT.dAuth
    requester = body.get(self.const.BASE_CT.BCctbase.SENDER)

      
    data[dAuthConst.DAUTH_SERVER_INFO] = {
      dAuthConst.DAUTH_SENDER_ETH : sender_eth_address,
      dAuthConst.DAUTH_SENDER_TYPE : version_check_data.requester_type,
      # "info" : str(version_check_data), 
    }

    if self.cfg_dauth_verbose:
      data[dAuthConst.DAUTH_REQUEST] = body

    return data
  
  
  
  def process_dauth_request(self, body):
        
    dAuthConst = self.const.BASE_CT.dAuth
    data = {
      dAuthConst.DAUTH_SUBKEY : {
        'error' : None,
      },
    }
    dct_dauth = data[dAuthConst.DAUTH_SUBKEY]
    error = None
    _non_critical_error = None
    requester = body.get(self.const.BASE_CT.BCctbase.SENDER)
    requester_eth = self.__internal_to_eth(requester)    
    self.Pd("Received request from {} for auth:\n{}".format(
      requester, self.json_dumps(body, indent=2))
    )
    
    ###### verify the request signature ######
    verify_data = self.bc_direct.verify(body, return_full_info=True)
    if not verify_data.valid:
      error = 'Invalid request signature: {}'.format(verify_data.message)

    ###### basic version checks ######
    version_check_data : VersionCheckData = self.version_check(body)
    if not version_check_data.result:
      # not None means we have a error message
      error = 'Version check failed: {}'.format(version_check_data.message)
    elif version_check_data.message not in [None, '']:
      _non_critical_error = version_check_data.message

    ###### check if node_address is allowed ######   
    allowed_to_dauth = self.check_if_node_allowed(
      node_address=requester, node_address_eth=requester_eth, version_check_data=version_check_data
    )
    if not allowed_to_dauth:
      error = 'Node not allowed to request auth data.'      
    
    if error is not None:
      dct_dauth['error'] = error
      self.Pd("Error on request from {}: {}".format(requester, error), color='r')
    else:
      if _non_critical_error is not None:
        dct_dauth['error'] = _non_critical_error
        self.Pd("Non-critical error on request from {}: {}".format(requester, _non_critical_error))
      self.fill_dauth_data(dct_dauth)
              
      # record the node_address and the auth data      
      self.chainstore_store_dauth_request(
        node_address=requester, node_address_eth=requester_eth, 
        dauth_data=data
      )
    #end no errors
    
    self.fill_extra_info(
      data=data, body=body, sender_eth_address=requester_eth,
      version_check_data=version_check_data
    )
    return data
      
  
if __name__ == '__main__':
  import json
  import os

  import naeural_core.constants as ct
  from naeural_client._ver import __VER__ as sdk_ver
  from naeural_core.main.ver import __VER__ as core_ver
  from constants import ADMIN_PIPELINE
    
  from naeural_client.bc import DefaultBlockEngine
  from naeural_client import Logger
  from ver import __VER__ as ee_ver
  
  l = Logger("DAUTH", base_folder=".", app_folder="_local_cache")
  bc = DefaultBlockEngine(log=l, name="default")
  
  eng = _DauthMixin()
  eng.const = ct
  eng.bc_direct = bc
  eng.cfg_dauth_verbose = True
  eng.P = l.P
  eng.json_dumps = json.dumps
  eng.ee_ver = ee_ver
  eng.ee_core_ver = core_ver
  eng.ee_sdk_ver = sdk_ver
  eng.os_environ = os.environ
  eng.cfg_auth_env_keys = ADMIN_PIPELINE["DAUTH_MANAGER"]["AUTH_ENV_KEYS"]
  eng.cfg_auth_predefined_keys = ADMIN_PIPELINE["DAUTH_MANAGER"]["AUTH_PREDEFINED_KEYS"]
  
  
  
  request = {
      "sender_alias": "test1",
      "nonce": "a14473a1",
      "sender_app_ver": None,
      "sender_sdk_ver": "2.6.29",
      "sender_core_ver": None,
      "EE_SIGN": "MEQCIAnXNWxcskr_2zj5kGRFQobJdDVovA57J_WMphFIOCf7AiAkDE7P446N4mQCAO2OAnQvW7PCdLNsRsHvGkBEz-BL4Q==",
      "EE_SENDER": "0xai_AjcIThkOqrPlp35-S8czHUOV-y4mnhksnLs8NGjTbmty",
      "EE_ETH_SENDER": "0x13Dc6Ee23D45D1e4bF0BDBDf58BFdF24bB077e69",
      "EE_ETH_SIGN": "0xBEEF",
      "EE_HASH": "e6a3f87d035b632c119cf1cacf02fcda79887fa24b3fa6355f6ec26b6c6cae70"
  }
  
  res = eng.process_dauth_request(request)
  l.P(f"Result:\n{json.dumps(res, indent=2)}")
      
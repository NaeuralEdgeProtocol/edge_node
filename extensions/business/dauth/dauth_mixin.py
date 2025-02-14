
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
  def __init__(self, result=False, message="", requester_type=None):
    self.result = result
    self.message = message
    self.requester_type = requester_type
    return
  
### START OF MIXIN ###

class _DauthMixin(object):

  def __init__(self):
    super(_DauthMixin, self).__init__()    
    return

  def Pd(self, s, *args, **kwargs):
    """
    Print a message to the console.
    """
    if self.cfg_dauth_verbose:
      s = "[DDBG] " + s
      self.P(s, *args, **kwargs)
    return  

  
  def version_check(
    self, 
    sender_app_version : str,
    sender_core_version : str,
    sender_sdk_version : str
  ):
    """
    Check the version of the node that is sending the request.
    Returns `None` if all ok and a message if there is a problem.
    
    
    """    
    #
    output = VersionCheckData(result=True, message="")
    dAuthCt = self.const.BASE_CT.dAuth
    int_sender_app_version = version_to_int(sender_app_version)
    int_sender_core_version = version_to_int(sender_core_version)
    int_sender_sdk_version = version_to_int(sender_sdk_version)
    int_server_app_version = version_to_int(self.ee_ver)
    int_server_core_version = version_to_int(self.ee_core_ver)
    int_server_sdk_version = version_to_int(self.ee_sdk_ver)
    
    if int_sender_app_version == 0 and int_sender_core_version == 0 and int_sender_sdk_version > 0:
      output.requester_type = dAuthCt.DAUTH_SENDER_TYPE_SDK
      output.message += f"SDK v{sender_sdk_version} accepted for dAuth request."
    elif int_sender_app_version == 0 and int_sender_core_version >0 and int_sender_sdk_version > 0:
      output.requester_type = dAuthCt.DAUTH_SENDER_TYPE_CORE
      output.result = False # we should block this
      output.message += "Invalid sender version data - core and sdk only not allowed for dAuth"
    elif int_sender_app_version > 0 and int_sender_core_version > 0 and int_sender_sdk_version > 0:
      output.requester_type = dAuthCt.DAUTH_SENDER_TYPE_NODE
      output.message += f"Edge Node v{sender_app_version} pre-accepted for dAuth request."
    else:
      output.requester_type = "unknown"
      output.result = False
      output.message += "Invalid sender version data."
    
    if int_sender_app_version > 0 and int_sender_app_version < int_server_app_version:
      output.message += f" Sender app version {sender_app_version} is lower than server app version {self.ee_ver}."
      # maybe we should block below a certain level
    if int_sender_core_version > 0 and int_sender_core_version < int_server_core_version:
      output.message += f" Sender core version {sender_core_version} is lower than server core version {self.ee_core_ver}."
      # maybe we should block below a certain level
    if int_sender_sdk_version > 0 and int_sender_sdk_version < int_server_sdk_version:
      output.message += f" Sender sdk version {sender_sdk_version} is lower than server sdk version {self.ee_sdk_ver}."
    elif int_sender_sdk_version != int_server_sdk_version:
      output.message += f" Sender sdk version {sender_sdk_version} is different from server sdk version {self.ee_sdk_ver}."
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
    self.Pd(f"Checking if node {node_address} (ETH: {node_address_eth}) is allowed")
    msg = ""
    result = True    
    if not version_check_data.result:
      result = False
      msg = "Version check failed: {}".format(version_check_data.message)
    else:
      try:
        if version_check_data.requester_type != self.const.BASE_CT.dAuth.DAUTH_SENDER_TYPE_SDK:
          result = self.bc.is_node_licensed(node_address_eth=node_address_eth)
          str_allowed = "allowed" if result else "not allowed"
          msg = f"node {node_address_eth} {str_allowed} on {self.evm_network}"
      except Exception as e:
        result = False
        msg = "Error checking if node is allowed ({} on {}): {} ".format(
          node_address_eth, self.evm_network, e
        )
    return result, msg
  
  
  def chainstore_store_dauth_request(
    self, 
    node_address : str, 
    node_address_eth : str, 
    dauth_data : dict,
    sender_nonce : str,
  ):
    """
    Set the chainstore data for the requester.
    
    
    """
    self.Pd("CSTORE dAuth request '{}' data for node {} ({})".format(
      sender_nonce, node_address, node_address_eth)
    )
    return
  
  
  def fill_dauth_data(self, dauth_data, requester_node_address):
    """
    Fill the data with the authentication data.
    """
    dAuthCt = self.const.BASE_CT.dAuth
    
    ## TODO: review this section:
    ##         maybe we should NOT use the default values or maybe we should just use the default values
    lst_auth_env_keys = self.cfg_auth_env_keys
    dct_auth_predefined_keys = self.cfg_auth_predefined_keys
    
    default_env_keys = self.const.ADMIN_PIPELINE["DAUTH_MANAGER"]["AUTH_ENV_KEYS"]
    default_predefined_keys = self.const.ADMIN_PIPELINE["DAUTH_MANAGER"]["AUTH_PREDEFINED_KEYS"]
    lst_auth_env_keys = list(set(lst_auth_env_keys + default_env_keys))
    dct_auth_predefined_keys = {**dct_auth_predefined_keys, **default_predefined_keys}
    
    if lst_auth_env_keys is None:
      raise ValueError("No auth env keys defined (AUTH_ENV_KEYS==null). Please check the configuration!")
    
    if dct_auth_predefined_keys is None:
      raise ValueError("No predefined keys defined (AUTH_PREDEFINED_KEYS==null). Please check the configuration")
    
    ### get the mandatory oracles whitelist and populate answer  ###  
    oracles, oracles_names, oracles_eth = self.bc.get_oracles(include_eth_addrs=True)   
    self.Pd(f"Oracles on {self.evm_network}: {oracles_eth}")
    full_whitelist = [
      a + (f"  {b}" if len(b) > 0 else "") 
      for a, b in zip(oracles, oracles_names)
    ]
    dauth_data[dAuthCt.DAUTH_WHITELIST] = full_whitelist

    #####  finally prepare the env auth data #####
    for key in lst_auth_env_keys:
      if key.startswith(dAuthCt.DAUTH_ENV_KEYS_PREFIX):
        dauth_data[key] = self.os_environ.get(key)
    
    # overwrite the predefined keys
    for key in dct_auth_predefined_keys:
      dauth_data[key] = dct_auth_predefined_keys[key]
    
    # set the supervisor flag if this is identified as an oracle
    if requester_node_address in oracles:
      dauth_data["EE_SUPERVISOR"] = True
      for key in self.cfg_supervisor_keys:
        if isinstance(key, str) and len(key) > 0:
          dauth_data[key] = self.os_environ.get(key)
        # end if
      # end for
    # end set supervisor flag

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
    """
    This is the main method that processes the request for authentication.
    """
    error = None
    _non_critical_error = None
    requester_eth = None
    version_check_data = VersionCheckData(result=False, message="", requester_type=None)
        
    dAuthConst = self.const.BASE_CT.dAuth
    
    data = {
      dAuthConst.DAUTH_SUBKEY : {
        'error' : None,
      },
    }
    dct_dauth = data[dAuthConst.DAUTH_SUBKEY]
    
    sender_nonce = body.get(dAuthConst.DAUTH_NONCE)
    
    requester = body.get(self.const.BASE_CT.BCctbase.SENDER)
    requester_send_eth = body.get(self.const.BASE_CT.BCctbase.ETH_SENDER)
    requester_alias = body.get("sender_alias")
    
    sender_app_version = body.get(dAuthConst.DAUTH_SENDER_APP_VER)
    sender_core_version = body.get(dAuthConst.DAUTH_SENDER_CORE_VER)
    sender_sdk_version = body.get(dAuthConst.DAUTH_SENDER_SDK_VER)            
                
    if requester is None:
      error = 'No sender address in request.'
      
    if error is None:
      try:
        requester_eth = self.bc.node_address_to_eth_address(requester)
        if requester_eth != requester_send_eth:
          error = 'Sender eth address and recovered eth address do not match.'  
        else:
          self.Pd("dAuth req from '{}' <{}> | <{}>, app:{}, core:{}, sdk:{}".format(
            requester_alias, requester, requester_eth,
            sender_app_version, sender_core_version, sender_sdk_version
          ))
      except Exception as e:
        error = 'Error converting node address to eth address: {}'.format(e)
    
    ###### verify the request signature ######
    if error is None:
      verify_data = self.bc.verify(body, return_full_info=True)
      if not verify_data.valid:
        error = 'Invalid request signature: {}'.format(verify_data.message)

    ###### basic version checks ######
    if error is None:
      version_check_data : VersionCheckData = self.version_check(
        sender_app_version=sender_app_version,
        sender_core_version=sender_core_version,
        sender_sdk_version=sender_sdk_version
      )
      if not version_check_data.result:
        # not None means we have a error message
        error = 'Version check failed: {}'.format(version_check_data.message)
      elif version_check_data.message not in [None, '']:
        _non_critical_error = version_check_data.message

    ###### check if node_address is allowed ######   
    if error is None:
      allowed_to_dauth, message = self.check_if_node_allowed(
        node_address=requester, node_address_eth=requester_eth, 
        version_check_data=version_check_data
      )
      if not allowed_to_dauth:
        error = 'Node not allowed to request auth data. ' + message
    
    ####### now we prepare env variables ########
    short_requester = requester[:8] + '...' + requester[-4:]
    short_eth = requester_eth[:6] + '...' + requester_eth[-4:]
    if error is not None:
      dct_dauth['error'] = error
      self.P("dAuth request '{}' failed for <{}>  '{}' (ETH: {}): {}".format(
        sender_nonce, short_requester, requester_alias, short_eth, error), color='r'
      )
    else:
      if _non_critical_error is not None:
        dct_dauth['error'] = _non_critical_error
        self.Pd("Non-critical error on request from {}: {}".format(requester, _non_critical_error))
      ### Finally we fill the data with the authentication data
      self.fill_dauth_data(dct_dauth, requester_node_address=requester)
      self.P("dAuth req '{}' success for <{}> '{}' (ETH: {})".format(
        sender_nonce, short_eth, requester_alias, short_eth)
      )
      ### end fill data
              
      # record the node_address and the auth data      
      self.chainstore_store_dauth_request(
        node_address=requester, node_address_eth=requester_eth, 
        dauth_data=data, sender_nonce=sender_nonce
      )
    #end no errors
    
    ####### add some extra info to payloads ########
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
  from naeural_core.utils.plugins_base.bc_wrapper import BCWrapper
  
    
  from naeural_client.bc import DefaultBlockEngine
  from naeural_client import Logger
  from ver import __VER__ as ee_ver
  
  l = Logger("DAUTH", base_folder=".", app_folder="_local_cache")
  bc_eng = DefaultBlockEngine(log=l, name="default")
  
  bc = BCWrapper(bc_eng, owner=l)
  
  
  os.environ['EE_EVM_NET'] = 'testnet'
  eng = _DauthMixin()
  eng.const = ct
  eng.bc = bc
  eng.evm_network = bc.get_evm_network()
  eng.cfg_dauth_verbose = True
  eng.P = l.P
  eng.json_dumps = json.dumps
  eng.ee_ver = ee_ver
  eng.ee_core_ver = core_ver
  eng.ee_sdk_ver = sdk_ver
  eng.os_environ = os.environ
  eng.cfg_auth_env_keys = ADMIN_PIPELINE["DAUTH_MANAGER"]["AUTH_ENV_KEYS"]
  eng.cfg_auth_predefined_keys = ADMIN_PIPELINE["DAUTH_MANAGER"]["AUTH_PREDEFINED_KEYS"]
  
  
  
  request_sdk = {
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
  
  request_bad_node = {
      "nonce": "74c4629f",
      "sender_app_ver": "2.7.27",
      "sender_sdk_ver": "2.7.27",
      "sender_core_ver": "7.6.61",
      "sender_alias": "test1",
      "EE_SIGN": "MEUCIEmnPjCNwsSAlGANkT16IWMV4clYY4RoistByxIBIqJaAiEAsVSFSa3gip4TtiV-35PAjYZLVAdcIjJOJIT7_L4BxUI=",
      "EE_SENDER": "0xai_AlgFNEkQMDvLLKW4EzxPN038XCH3vAC8ClO73LbG7N8K",
      "EE_ETH_SENDER": "0x2f7B47edF44a1eD1ED04099F1beaf1aCb8176498",
      "EE_ETH_SIGN": "0xBEEF",
      "EE_HASH": "6e8b5267f163d7bdb476cbb75d305c755bfb9534be7aee9083c142d9d371de9c"
    }
  
  
  request_faulty = {
    "EE_SENDER" : "0xai_AjcIThkOqrPlp35-S8czHUOV-y4mnhksnLs8NGjTbmty",
  }
  
  # res = eng.process_dauth_request(request_faulty)
  res = eng.process_dauth_request(request_sdk)
  # res = eng.process_dauth_request(request_bad)
  l.P(f"Result:\n{json.dumps(res, indent=2)}")
      
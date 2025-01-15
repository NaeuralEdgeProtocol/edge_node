
import json


from naeural_client import Logger, const
from naeural_client.bc import DefaultBlockEngine



if __name__ == '__main__' :
  l = Logger("ENC", base_folder=".", app_folder="_local_cache")
  eng1 = DefaultBlockEngine(
    log=l, name="test1", 
    config={
        "PEM_FILE"     : "nen2.pem",
        "PASSWORD"     : None,      
        "PEM_LOCATION" : "data"
      }
  )
  eng2 = DefaultBlockEngine(
    log=l, name="test2", 
    config={
        "PEM_FILE"     : "test2.pem",
        "PASSWORD"     : None,      
        "PEM_LOCATION" : "data"
      }
  )
    
  l.P(eng1.eth_address)
  l.P(eng1.eth_account.address)
  l.P(eng1.eth_address == eng1.eth_account.address)

   
  node = "0xai_AvuUcmXyn6U3z8XRagqG8_d2sKCDZ5FIDpkUlpUz3Iuh"
  node_eth = eng1.node_address_to_eth_address(node)
  l.P("Node: {}\nNode Eth: {}".format(node, node_eth))
  epochs = [290, 291, 292]
  epochs_vals = [254, 0, 242]
  USE_ETH_ADDR = True
  
  if USE_ETH_ADDR:  
    types = ["address", "uint256[]", "uint256[]"]
    node_data = node_eth
  else:
    types = ["string", "uint256[]", "uint256[]"]
    node_data = node
    
  values = [node_data, epochs, epochs_vals]
  
 
  s2 = eng1.eth_sign_message(types, values)
  l.P("Results:\n{}".format(json.dumps(s2, indent=2)))
  l.P("Signature: {}".format(eng1.eth_sign_node_epochs(node_data, epochs, epochs_vals)))

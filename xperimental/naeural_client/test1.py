"""
This is a simple example of how to use the naeural_client SDK.

In this example, we connect to the network, listen for heartbeats from 
  Naeural Edge Protocol edge nodes and print the CPU of each node.
"""
import json

from naeural_client import Session, Payload


class MessageHandler:
  def __init__(self, signature_filter: str = None):
    """
    This class is used to handle the messages received from the edge nodes.
    """
    self.signature_filter = signature_filter.upper() if isinstance(signature_filter, str) else None
    self.last_data = None # some variable to store the last data received for debugging purposes
    return
  
  def shorten_address(self, address):
    """
    This method is used to shorten the address of the edge node.
    """
    return address[:8] + "..." + address[-6:]
  
  def on_heartbeat(self, session: Session, node_addr: str, heartbeat: dict):
    """
    This method is called when a heartbeat is received from an edge node.
    
    Parameters
    ----------
    session : Session
        The session object that received the heartbeat.
        
    node_addr : str
        The address of the edge node that sent the heartbeat.
        
    heartbeat : dict
        The heartbeat received from the edge node.        
    """
    session.P("{} ({}) has a {}".format(
      heartbeat['EE_ID'], 
      self.shorten_address(node_addr), 
      heartbeat["CPU"])
    )
    return

  def on_data(
    self,
    session: Session, 
    node_addr : str, 
    pipeline_name : str, 
    plugin_signature : str, 
    plugin_instance : str,  
    data : Payload      
  ):
    """
    This method is called when a payload is received from an edge node.
    
    Parameters
    ----------
    
    session : Session
        The session object that received the payload.
        
    node_addr : str
        The address of the edge node that sent the payload.
        
    pipeline_name : str
        The name of the pipeline that sent the payload.
        
    plugin_signature : str
        The signature of the plugin that sent the payload.
        
    plugin_instance : str
        The instance of the plugin that sent the payload.
        
    data : Payload
        The payload received from the edge node.      
    """
    addr = self.shorten_address(node_addr)
    
    if self.signature_filter is not None and plugin_signature.upper() != self.signature_filter:
      # we are not interested in this data but we still want to log it
      message = "Received data from <{}::{}::{}::{}>".format(
        addr, pipeline_name, plugin_signature, plugin_instance
      )
      color = 'dark'
    else:
      # we are interested in this data
      message = "Received target data from <{}::{}::{}::{}>\n".format(
        node_addr, pipeline_name, plugin_signature, plugin_instance
      )
      # the actual data is stored in the data.data attribute of the Payload UserDict object
      # now we just copy some data as a naive example
      self.last_data = {
        k:v for k,v in data.data.items() 
        if k in ["EE_HASH", "EE_IS_ENCRYPTED", "EE_MESSAGE_SEQ", "EE_SIGN", "EE_TIMESTAMP"]
      }
      message += "{}".format(json.dumps(self.last_data, indent=2))
      color = 'g'
    session.P(message, color=color)
    return


if __name__ == '__main__':
  # create a naive message handler   
  filterer = MessageHandler("REST_CUSTOM_EXEC_01")
  
  # create a session
  # the network credentials are read from the .env file automatically
  session = Session(
      on_heartbeat=filterer.on_heartbeat,
      on_payload=filterer.on_data,
  )


  # Observation:
  #   next code is not mandatory - it is used to keep the session open and cleanup the resources
  #   in production, you would not need this code as the script can close after the pipeline will be sent
  session.run(
    wait=30, # wait for the user to stop the execution or a given time
    close_pipelines=True # when the user stops the execution, the remote edge-node pipelines will be closed
  )
  session.P("Main thread exiting...")

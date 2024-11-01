# -*- coding: utf-8 -*-
"""



"""
from naeural_core.data.base import BaseStructuredDataCapture

_CONFIG = {
  **BaseStructuredDataCapture.CONFIG,
  
  'CAP_RESOLUTION'    : 0.5, 
  'EXTRA_DEBUG_INFO'  : False,
  'CONNECTION_DATA'   : 100,
  
  'VALIDATION_RULES' : {
    **BaseStructuredDataCapture.CONFIG['VALIDATION_RULES'],
  },
}

class StructStreamTutorialDataCapture(BaseStructuredDataCapture):
  
  def __maybe_break_connection(self):
    if self.np.random.randint(0, 100) < 10:
      self.has_connection = False
      self.P("Simulated connection loss", color='r')
      # serialization
      self.cacheapi_save_json(self.__connection_data, verbose=True)
    #endif      
    return


  def on_init(self):
    """
    This method is called once, just before the plugin is initialized.
    """
    self.P("Pre-initialization of connection and other stuff...")
    # setup a variables that can be passed downstream
    self._metadata.reconnects_from_restart = 0
    self._metadata.number_of_data_captures = 0
    return

  def connect(self):
    """
    Called each time a connection is required due to start or lost connection.
    """
    failure_rate = 0.05
    # simulate connection failure 10% of the time
    if self.np.random.randint(0, 100) < failure_rate * 100:
      self.P("Simulated failure to connect", color='r')
      success = False
    else:
      # some default connection data
      default_connection_data = {
        "curr_val" : 0,
        "reconn_lifetime" : 0,
        "nr_observations" : 0,
      }
      config_connection_value = self.cfg_connection_data
      # load persistent data flow 
      self.__connection_data = self.cacheapi_load_json(default=default_connection_data, verbose=True) 
      # simulate a connection reset
      self.__connection_data['curr_val'] = self.__connection_data['curr_val'] + config_connection_value 
       # increment the number of reconnects from restart in the metadata (if we want)
      self._metadata.reconnects_from_restart += 1
      # increment the number of lifetune reconnects for persistence (if we want)
      self.__connection_data['reconn_lifetime'] += 1 
      # send also as metadata (if we want)
      self._metadata.reconnects_lifetime = self.__connection_data['reconn_lifetime'] 
      
      self.P("Reconnected #{}, lifetime #{}, value: {}".format(
        self._metadata.reconnects_from_restart,
        self._metadata.reconnects_lifetime,
        self.__connection_data['curr_val']
      ))
      success = True
    #endif
    return success

  
  def get_data(self): 
    """
    Get a data observation from the target structured data source.
    """ 
    # get some random walk data
    some_value = self.np.random.randint(0, 100) / 1000
    self.__connection_data['curr_val'] += some_value
    self.__connection_data['curr_val'] = round(self.__connection_data['curr_val'], 3)
    nr_observations = self.__connection_data.get('nr_observations', 0)
    self.__connection_data['nr_observations'] = nr_observations + 1    
    
    value = self.__connection_data['curr_val']
    data_observation = {'OBS' : value}
    self._metadata.number_of_data_captures += 1
    self._metadata.number_of_lifetime_data_captures = self.__connection_data['nr_observations']
    
    # connection failure simulation
    self.__maybe_break_connection()    
    return data_observation
  
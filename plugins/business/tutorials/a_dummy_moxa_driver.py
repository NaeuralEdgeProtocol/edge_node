from naeural_core.business.base import BasePluginExecutor
from naeural_core.business.mixins_base import MoxaE1214Device

__VER__ = '0.1.0.0'

_CONFIG = {
  **BasePluginExecutor.CONFIG,

  'ALLOW_EMPTY_INPUTS': True,

  "PROCESS_DELAY": 1,

  'DEVICE_IP': None,

  'DEVICE_CACHE_TIMEOUT': 500,

  'DEVICE_DEBOUNCE': 3,  # seconds

  'VALIDATION_RULES': {
    **BasePluginExecutor.CONFIG['VALIDATION_RULES'],
  },
}

"""
The MoxaE1214Device provides several methods to interact with the device.
The methods are grouped into three categories:
    - system info
    - digital pins
    - relay pins
    
The system info methods are:
    - get_system_info()
    - update(with_system_info=False)
    - commit()
    
The digital pin methods are:
    - get_digital_pin(index: int)
    - get_digital_pins()
    - set_digital_pin(index: int, value: int) -> bool
    
The relay pin methods are:
    - get_relay_pin(index: int)
    - get_relay_pins()
    - set_relay_pin(index: int, value: int) -> bool
"""


class ADummyMoxaDriver(BasePluginExecutor, MoxaE1214Device):
  CONFIG = _CONFIG

  def __init__(self, **kwargs):
    super(ADummyMoxaDriver, self).__init__(**kwargs)
    """
    Call the update method to initialize the device
    Passing with_system_info=True will also fetch the system info such as device model and uptime
    """
    self.update(with_system_info=True)
    return

  def startup(self):
    super().startup()
    return

  def _on_command(self, data, **kwargs):
    """
    This method is called when a command is received from the server a.k.a instance command
    Parameters
    ----------
    data
    kwargs

    Returns
    -------

    """
    payload = None
    """ 
    Assuming we want to toggle a relay we can make use of the MoxaE1214Device.set_relay_pin() method
    to toggle the relay state. The method accepts the relay index and the state to set.
    """
    if isinstance(data, dict) and "action" in data and data["action"] == "TOGGLE_RELAY":
      self.set_relay_pin(index=data["relay_index"], value=data["relay_state"])
      """
      In order for the changes to take effect we need to commit the changes to the device.
      Calling the MoxaE1214Device.commit() method will do just that.
      """
      self.commit()
    # endif toggle relay

    """
    Assuming we want to fetch the current state of the relay pins we can make use of the
    MoxaE1214Device.get_relay_pins() method to fetch the current state of the relay pins.
    The method returns a list of relay pins from the current snapshot of the device.
    
    For the most up-to-date information we can call the MoxaE1214Device.update() method
    """
    if isinstance(data, dict) and "action" in data and data["action"] == "GET_RELAY_PINS":
      self.update()
      relays = self.get_relay_pins()
      payload = {
        "relays": relays
      }
    # endif get relays
    return payload

  def _process(self):
    """
    This method is called periodically by the plugin manager.
    Returns
    -------

    """

    """
    We can make use of this behavior to periodically fetch the current state of the device.
    """
    self.update()

    """
    Now that we've updated the device state we can preform various actions depending on the
    current state of the device.
    """
    payload = None

    if self.get_digital_pin(index=0) == 1:
      """
      If the first digital input pin is high we can send a message to the server.
      """
      payload = {
        "message": "Hello World!"
      }

      """
      In order to publish the above payload we need to call the _create_payload() method.
      """
      payload = self._create_payload(payload=payload)
    # endif digital pin 0 is high

    return payload

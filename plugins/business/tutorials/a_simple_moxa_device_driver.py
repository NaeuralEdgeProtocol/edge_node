"""
In this tutorial we are going to demonstrate how to create a simple driver for a moxa device.
We are going to use the MoxaCustomDevice as a base class for the driver.
The MoxaCustomDevice is a base class that implements Moxa specific logic.

This is an example pipeline that uses the moxa driver:
{
    "INSTANCES": [
        {
            "FORCED_PAUSE": false,
            "DEVICE_IP": "1.1.1.1",
            "INSTANCE_ID": "INSTANCE_1",
        }
    ],
    "SIGNATURE": "A_SIMPLE_HORN_SPEAKER_DRIVER"
}

This is an example instance command that the moxa driver can receive:
"INSTANCE_COMMAND": {
    "action": "SET_STATE",
    "relays": [
        {
            "index": 1,
            "value": 1
        },
        {
            "index": 2,
            "value": 0
        }
    ]
}

In the above example, the driver will change the state of the relay with index 1 to a value of 1 and
the state of the relay with index 2 to a value of 0.

Note that although the driver is capable of handling multiple relays, the moxa device used in this
can only handle one relay at a time.

By passing the "action" parameter, we can specify what method will be called by the plugin
upon receiving and instance command.

Note that in order for your method to be called, it must be prefixed with "action_" and the
value of the "action" parameter must be in uppercase and follow the snakecase convention.

For example if the value of the "action" parameter is "SET_STATE", the method that will be called
is "action_set_state".

Another example will be if the value of the "action" parameter is "READ_RELAY_PINS", the method that
is called is "action_read_relay_pins".

If a method is not found, the driver will print an error message and return None.
"""
from core.business.base.drivers.custom.moxa_custom_device import MoxaCustomDevice


class ASimpleMoxaDeviceDriverPlugin(MoxaCustomDevice):
  def __init__(self, **kwargs):
    super(ASimpleMoxaDeviceDriverPlugin, self).__init__(**kwargs)
    return

  def action_set_state(self, relays, **kwargs):
    """
    Set the state of the relays
    This method is called when the client sends a command to set the state of the relays
    If multiple relays are requested, the code will iterate over the relays and set the state of each one

    Parameters
    ----------
    relays : list
    kwargs : dict

    Returns
    -------

    """
    if not isinstance(relays, list):
      self.P(f"Invalid relays {relays}", color="red")
      return

    for relay in relays:
      self._moxa_set_relay_pin(index=int(relay["index"]), value=int(relay["value"]))
    return

from naeural_core.business.test_framework.base import BaseTestingPlugin

class AlertsTestingPlugin(BaseTestingPlugin):
  def __init__(self, **kwargs):
    super(AlertsTestingPlugin, self).__init__(**kwargs)
    return

  @property
  def cfg_key_is_alert(self):
    return self.config.get("KEY_IS_ALERT", "IS_ALERT")

  @property
  def cfg_key_is_new_raise(self):
    return self.config.get("KEY_IS_NEW_RAISE", "IS_NEW_RAISE")

  @property
  def cfg_key_is_new_lower(self):
    return self.config.get("KEY_IS_NEW_LOWER", "IS_NEW_LOWER")


  def startup(self):
    super().startup()
    self.y_hat = []
    return

  def _register_payload(self, payload):
    crt_time = payload['_T_CRT_TIME']

    is_alert = payload.get(self.cfg_key_is_alert, None)
    if is_alert is None:
      return

    is_new_raise = payload.get(self.cfg_key_is_new_raise, True)
    is_new_lower = payload.get(self.cfg_key_is_new_lower, True)
    if is_alert:
      if is_new_raise:
        self.y_hat.append({"TIMESTAMP" : crt_time, "ALERT" : "RAISE"})
    else:
      if is_new_lower:
        self.y_hat.append({"TIMESTAMP" : crt_time, "ALERT" : "LOWER"})
    #endif

    return

from naeural_core.business.test_framework.base import BaseTestingPlugin

class IntervalsCountingTestingPlugin(BaseTestingPlugin):

  def __init__(self, **kwargs):
    super(IntervalsCountingTestingPlugin, self).__init__(**kwargs)
    return
  
  @property
  def cfg_key_start_interval(self):
    return self.config.get("KEY_START_INTERVAL", "START_INTERVAL")

  @property
  def cfg_key_end_interval(self):
    return self.config.get("KEY_END_INTERVAL", "END_INTERVAL")

  @property
  def cfg_key_count(self):
    return self.config.get("KEY_COUNT", "COUNT")

  def startup(self):
    super().startup()
    self.y_hat = []
    return

  def _register_payload(self, payload):
    if any([x not in payload for x in [self.cfg_key_start_interval, self.cfg_key_end_interval, self.cfg_key_count]]):
      return

    self.y_hat.append(
      {
        "START" : payload[self.cfg_key_start_interval],
        "END"   : payload[self.cfg_key_end_interval],
        "COUNT" : payload[self.cfg_key_count]
      }
    )

    return

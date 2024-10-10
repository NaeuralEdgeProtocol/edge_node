from naeural_core.business.test_framework.base import BaseTestingPlugin


class SimpleCountingTestingPlugin(BaseTestingPlugin):

  def __init__(self, **kwargs):
    super(SimpleCountingTestingPlugin, self).__init__(**kwargs)
    return

  @property
  def cfg_key_error_margin(self):
    return self.config.get("KEY_ERROR_MARGIN", "ERROR_MARGIN")

  @property
  def cfg_key_count(self):
    return self.config.get("KEY_COUNT", "COUNT")

  def startup(self):
    super().startup()
    self.y_hat = []
    return

  def _register_payload(self, payload):
    if self.cfg_key_count not in payload:
      return

    self.y_hat.append(
      {
        "COUNT": payload[self.cfg_key_count],
        "ERROR_MARGIN" : payload.get(self.cfg_key_error_margin, 0)
      }
    )

    return
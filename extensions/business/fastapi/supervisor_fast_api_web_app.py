from naeural_core.business.default.web_app.fast_api_web_app import FastApiWebAppPlugin as BasePlugin

__VER__ = '0.1.0.0'

_CONFIG = {
  **BasePlugin.CONFIG,

  'VALIDATION_RULES': {
    **BasePlugin.CONFIG['VALIDATION_RULES'],
  },
}


class SupervisorFastApiWebApp(BasePlugin):
  CONFIG = _CONFIG

  def on_init(self):
    self.__supervisor_fastapi_plugin_running = None
    super(SupervisorFastApiWebApp, self).on_init()
    return

  @property
  def __is_enabled(self):
    res = not self.cfg_disabled and self.cfg_ngrok_edge_label is not None and self.is_supervisor_node
    if res != self.__supervisor_fastapi_plugin_running:
      self.__supervisor_fastapi_plugin_running = res
      if res:
        self.P(f"{self.__class__.__name__} is enabled")
      else:
        self.P(
          f"{self.__class__.__name__} is disabled on non-super nodes.", 
          color='r', 
          boxed=True
        )
    # endif changed state
    return res

  def _process(self):
    if not self.__is_enabled:
      return None
    return super(SupervisorFastApiWebApp, self)._process()

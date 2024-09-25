from core.business.default.web_app.fast_api_web_app import FastApiWebAppPlugin as BasePlugin

__VER__ = '0.1.0.0'

_CONFIG = {
  **BasePlugin.CONFIG,
  'USE_NGROK': False,
  'NGROK_ENABLED': False,
  'NGROK_DOMAIN': None,
  'NGROK_EDGE_LABEL': None,

  'CODE_TIMEOUT': 10,
  'SAVE_PERIOD': 60,
  "PROCESS_DELAY": 0.2,

  'PORT': 5002,
  'ASSETS': 'plugins/business/fastapi/_sandbox',
  'JINJA_ARGS': {
    'html_files': [
      {
        'name': 'index.html',
        'route': '/',
        'method': 'get'
      }
    ]
  },
  'VALIDATION_RULES': {
    **BasePlugin.CONFIG['VALIDATION_RULES'],
  },
}


class NaeuralCodeSandboxPlugin(BasePlugin):
  CONFIG = _CONFIG

  def __init__(self, **kwargs):
    super(NaeuralCodeSandboxPlugin, self).__init__(**kwargs)
    self.last_persistence_save_ts = self.time()
    self.request_history = []
    return

  def on_init(self):
    super(NaeuralCodeSandboxPlugin, self).on_init()
    self.load_persistence_data()
    return

  def maybe_persistence_save(self, force=False):
    if force or self.time() - self.last_persistence_save_ts > self.cfg_save_period:
      self.last_persistence_save_ts = self.time()
      obj = {
        'request_history': self.request_history
      }
      self.persistence_serialization_save(obj)
    # endif save needed
    return

  def load_persistence_data(self):
    data = self.persistence_serialization_load()
    if data is not None:
      prev_history = data.get('request_history', [])
      self.request_history = self.request_history + prev_history
    return

  @BasePlugin.endpoint(method='get')
  def code_history(self):
    return self.request_history

  @BasePlugin.endpoint(method='post')
  def execute_remote_code(self, code: str, debug: bool = False):
    """
    Endpoint to execute custom code.
    Parameters
    ----------
    code : str
        The code to execute.
    debug : bool
        If True, the debug mode will be enabled.

    Returns
    -------
    """
    if len(code) == 0:
      return {'error': '"code" key should not be an empty string.'}
    self.request_history.append({'code': code, "debug": debug})
    result, errors, warnings, printed = None, None, [], []
    self.P(f'Executing code:\n{code}')
    b64_code, errors = self.code_to_base64(code, return_errors=True)
    if errors is not None:
      return {'error': errors}
    res = self.exec_code(
      str_b64code=b64_code,
      debug=debug,
      self_var='plugin',
      modify=True,
      return_printed=True,
      timeout=self.cfg_code_timeout
    )
    if isinstance(res, tuple):
      result, errors, warnings, printed = res
    return {
      'result': result,
      'errors': errors,
      'warnings': warnings,
      'prints': printed,
      'timestamp': self.time()
    }

  def process(self):
    super(NaeuralCodeSandboxPlugin, self).process()
    self.maybe_persistence_save()
    return


from core.business.base.web_app import FastApiWebAppPlugin

__VER__ = '0.1.0.0'

_CONFIG = {
  **FastApiWebAppPlugin.CONFIG,

  'ASSETS' : 'naeural_release_app',
  'JINJA_ARGS': {
    'html_files' : [
      {
        'name'  : 'index.html',
        'route' : '/',
        'method' : 'get'
      }
    ]
  },
  'VALIDATION_RULES': {
    **FastApiWebAppPlugin.CONFIG['VALIDATION_RULES'],
  },
}

class NaeuralReleaseAppPlugin(FastApiWebAppPlugin):

  CONFIG = _CONFIG

  def on_init(self, **kwargs):
    super(NaeuralReleaseAppPlugin, self).on_init(**kwargs)
    self._last_day_regenerated = (self.datetime.now() - self.timedelta(days=1)).day
    return

  def _regenerate_index_html(self):
    """
    Regenerate the index.html file.
    """
    # the index.html file is located at `./plugins/business/fastapi/naeural_release_app/assets/index.html`
    return

  def _maybe_regenerate_index_html(self):
    """
    Regenerate the html files if the last regeneration was more than X seconds ago
    ago.
    """
    current_day = self.datetime.now().day
    if current_day - self._last_day_regenerated >= 1:
      self._regenerate_index_html()
      self._last_day_regenerated = current_day
    
    return

  def process(self):
    self._maybe_regenerate_index_html()
    return
    
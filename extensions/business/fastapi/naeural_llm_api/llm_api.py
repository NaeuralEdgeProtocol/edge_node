from extensions.business.fastapi.assistant.naeural_assistant import NaeuralAssistantPlugin as BasePlugin


_CONFIG = {
  **BasePlugin.CONFIG,

  'PORT': 5006,
  'ASSETS': 'extensions/business/fastapi/naeural_llm_api',
  "JINJA_ARGS": {
    # Done in order for this API to not have user interface.
    'html_files': []
  },
  'VALIDATION_RULES': {
    **BasePlugin.CONFIG['VALIDATION_RULES'],
  },
}


class LlmApiPlugin(BasePlugin):
  CONFIG = _CONFIG




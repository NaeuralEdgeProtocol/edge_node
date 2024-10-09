from core.business.default.llm.llm_agent import LlmAgentPlugin as BasePlugin

_CONFIG = {
  # mandatory area
  **BasePlugin.CONFIG,

  # our overwritten props
  'AI_ENGINE': "llm_ro",

  'VALIDATION_RULES': {
    **BasePlugin.CONFIG['VALIDATION_RULES'],
  },
}


class RoLlamaAgentPlugin(BasePlugin):
  CONFIG = _CONFIG



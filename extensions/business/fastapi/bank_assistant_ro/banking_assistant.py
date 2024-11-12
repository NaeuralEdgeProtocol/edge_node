from extensions.business.fastapi.assistant.naeural_assistant import NaeuralAssistantPlugin as BasePlugin


_CONFIG = {
  **BasePlugin.CONFIG,

  'PORT': 5005,
  'ASSETS': 'extensions/business/fastapi/bank_assistant_ro',
  "TEMPLATE_SYS_INFO": {
    "juridic": "extensions/business/fastapi/bank_assistant_ro/assets/juridic_info.pkl",
    "fizic": "extensions/business/fastapi/bank_assistant_ro/assets/fizic_info.pkl",
    # "juridic": "Esti un asistent bancar specializat pe persoanele juridice si vrei sa ajuti oameni.",
    # "fizic": "Esti un asistent bancar specializat pe persoanele fizice si vrei sa ajuti oameni."
  },
  'VALIDATION_RULES': {
    **BasePlugin.CONFIG['VALIDATION_RULES'],
  },
}


class BankingAssistantPlugin(BasePlugin):
  CONFIG = _CONFIG

  def __init__(self, **kwargs):
    super(BankingAssistantPlugin, self).__init__(**kwargs)
    return

  def relevant_plugin_signatures_llm(self):
    return ['ro_llama_agent']

  def process_sys_info(self, system_info: str = None, **kwargs):
    """
    Process the system information before sending it to the agent.
    Parameters
    ----------
    system_info : str - the system information from the request

    Returns
    -------
    res : str - the system information
    """
    sys_info = super(BankingAssistantPlugin, self).process_sys_info(system_info, **kwargs)
    if len(sys_info) == 0:
      return "Esti un asistent bancar excelent care raspunde concis si vrea sa ajute oamenii."
    return f"Esti un asistent bancar excelent si raspunzi concis luand mereu in considerare: {sys_info}"

from urllib3 import request

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

  def compute_request_body_llm(self, request_id, body):
    """
    Compute the request body to be sent to the agent's pipeline.
    Parameters
    ----------
    request_id : str - the request id
    body : dict - the request body

    Returns
    -------
    to_send : dict - the request body to be sent to the agent's pipeline
    """
    request_dict = super(BankingAssistantPlugin, self).compute_request_body_llm(request_id, body)
    context = request_dict['STRUCT_DATA'][0]['system_info']
    request_dict['STRUCT_DATA'][0]['context'] = context
    request_dict['STRUCT_DATA'][0]['system_info'] = "Esti un asistent bancar excelent care raspunde concis si vrea sa ajute oamenii."
    return request_dict


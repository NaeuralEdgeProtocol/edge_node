from extensions.business.fastapi.assistant.naeural_assistant import NaeuralAssistantPlugin as BasePlugin
import pickle


_CONFIG = {
  **BasePlugin.CONFIG,

  'PORT': 5005,
  'ASSETS': 'extensions/business/fastapi/bank_assistant_ro',
  'VALIDATION_RULES': {
    **BasePlugin.CONFIG['VALIDATION_RULES'],
  },
}


class BankingAssistantPlugin(BasePlugin):
  CONFIG = _CONFIG

  def __init__(self, **kwargs):
    self.ro_banking_system_info = ""
    super(BankingAssistantPlugin, self).__init__(**kwargs)
    return

  def get_sys_info_path(self):
    return 'extensions/business/fastapi/bank_assistant_ro/assets/juridic_info.pkl'

  def on_init(self):
    super(BankingAssistantPlugin, self).on_init()
    if True:
      return "Esti un asistent bancar exceptional si vrei sa ajuti oamenii."
    pkl_path = self.get_sys_info_path()
    pkl_full_path = self.os_path.abspath(pkl_path)
    self.P(f'Loading system info from {pkl_path} | {pkl_full_path}')
    with open(self.get_sys_info_path(), 'rb') as f:
      juridic_info_pkl_base64 = pickle.load(f)
    self.ro_banking_system_info = bytes.fromhex(juridic_info_pkl_base64).decode('utf-8')
    return

  def relevant_plugin_signatures_llm(self):
    return ['ro_llama_agent']

  def get_system_info(self, system_info: str):
    return self.ro_banking_system_info

  @BasePlugin.endpoint(method="get")
  def system_info(self):
    return self.get_system_info(self.ro_banking_system_info)

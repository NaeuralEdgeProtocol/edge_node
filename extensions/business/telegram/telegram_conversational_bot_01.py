from naeural_core.business.base import BasePluginExecutor as BasePlugin
from extensions.business.mixins.telegram_mixin import _TelegramChatbotMixin

_CONFIG = {
  **BasePlugin.CONFIG,
  
  "PROCESS_DELAY"           : 5,
  "ALLOW_EMPTY_INPUTS"      : True,
  
  "SEND_STATUS_EACH"        : 60,
  
  "TELEGRAM_BOT_NAME"       : None,
  "TELEGRAM_BOT_TOKEN"      : None,
  
  "API_TOKEN"               : None,
  "SYSTEM_PROMPT"           : None,
  "AGENT_TYPE"              : "API",
  "RAG_SOURCE_URL"          : None,
  

  'VALIDATION_RULES' : {
    **BasePlugin.CONFIG['VALIDATION_RULES'],
  },  
}

class TelegramConversationalBot01Plugin(
  _TelegramChatbotMixin,
  BasePlugin,
  ):  
  CONFIG = _CONFIG

  
  def on_init(self):
    self.__token = self.cfg_telegram_bot_token
    self.__bot_name = self.cfg_telegram_bot_name
    
    self.__last_status_check = 0
    
    if self.__custom_handler is not None:
      self.P("Building and running the Telegram bot...")  
      self.bot_build(
        token=self.__token,
        bot_name=self.__bot_name,
        message_handler=self.bot_msg_handler,
        run_threaded=True,
      )      
      self.bot_run()
      self.__failed = False
    else:
      self.P("Custom reply executor could not be created, bot will not run", color='r')
      self.__failed = True
      raise ValueError("Custom reply executor could not be created")
    return
  
  def bot_msg_handler(self, message, user, **kwargs):
    result = message
    # here the request-wait-response logic
    return result
  

  def process(self):
    payload = None
    if (self.time() - self.__last_status_check) > self.cfg_send_status_each:
      self.__last_status_check = self.time()
      if not self.__failed:
        self.bot_dump_stats()
    return payload
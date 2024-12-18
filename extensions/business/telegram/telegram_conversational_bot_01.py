import requests

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
  "TEMPERATURE": 0.7,
  "API_MODEL_NAME": "gpt-3.5-turbo",
  "RESPONSE_ROUTE_API": None,
  "RESPONSE_ROUTE_HOSTED": None,
  "REQUEST_URL_API": None,
  "REQUEST_URL_HOSTED": None,

  'VALIDATION_RULES' : {
    **BasePlugin.CONFIG['VALIDATION_RULES'],
  },  
}


DEFAULT_RESPONSE_ROUTE_API = ['choices', 0, 'message', 'content']
DEFAULT_RESPONSE_ROUTE_HOSTED = ['result', 'text_response']
OPENAI_CHAT_URL = 'https://api.openai.com/v1/chat/completions'
HOSTED_AGENT_URL = 'https://llm-api.naeural.ai/llm_request'


class TelegramConversationalBot01Plugin(
  _TelegramChatbotMixin,
  BasePlugin,
):
  CONFIG = _CONFIG
  
  def on_init(self):
    self.__token = self.cfg_telegram_bot_token
    self.__bot_name = self.cfg_telegram_bot_name
    self.__user_data = {}
    
    self.__last_status_check = 0
    
    self.P("Building and running the Telegram bot...")
    self.bot_build(
      token=self.__token,
      bot_name=self.__bot_name,
      message_handler=self.bot_msg_handler,
      run_threaded=True,
    )
    self.bot_run()
    self.__failed = False
    return

  def get_api_token(self):
    return self.cfg_api_token or self.os_environ.get('EE_OPENAI')

  def get_response_route_api(self):
    return self.cfg_response_route_api or DEFAULT_RESPONSE_ROUTE_API

  def get_response_route_hosted(self):
    return self.cfg_response_route_hosted or DEFAULT_RESPONSE_ROUTE_HOSTED

  def get_request_url_api(self):
    return self.cfg_request_url_api or OPENAI_CHAT_URL

  def get_request_url_hosted(self):
    return self.cfg_request_url_hosted or HOSTED_AGENT_URL

  def check_request_error_api(self, response):
    return 'error' in response or 'error' in response.get('type', '')

  def check_request_error_hosted(self, response):
    return 'result' not in response or 'error' in response['result']

  def process_url_request(self, data, url, bearer_token=None, error_check_func=None, response_route=None):
    result = None
    try:
      headers = {
        'Content-Type': 'application/json',
      }
      if bearer_token is not None:
        headers['Authorization'] = f'Bearer {bearer_token}'
      # endif bearer_token provided
      response = requests.post(
        url,
        headers=headers,
        json=data,
      )
      json_data = response.json()
      if error_check_func is not None and error_check_func(json_data):
        self.P(f"URL request failed: {json_data}", color='r')
      else:
        if response_route is not None:
          for key in response_route:
            json_data = json_data[key]
          # endfor key in response_route
        # endif response_route provided
        result = json_data
      # endif error in result
    except Exception as e:
      self.P(f"URL request failed with exception: {e}", color='r')
    # endtry
    return result

  def get_response_api(self, user, message):
    user_data = self.__user_data[user]
    # Retrieve the system prompt
    sys_info = user_data.get('system_prompt')
    messages = [{'role': 'system', 'content': sys_info}] if sys_info is not None else []
    # Add the previous messages, if any
    messages += user_data.get('messages', [])
    # Add the current user message
    messages.append({'role': 'user', 'content': message})

    data = {
      'model': self.cfg_api_model_name,
      'temperature': self.cfg_temperature,
      'messages': messages
    }
    return self.process_url_request(
      data, url=self.get_request_url_api(), bearer_token=self.get_api_token(),
      error_check_func=self.check_request_error_api,
      response_route=self.get_response_route_api()
    )

  def __messages_to_history(self, messages):
    res = []
    current_turn = {}
    for msg in messages:
      if msg['role'] == 'user':
        current_turn['request'] = msg['content']
      elif msg['role'] == 'assistant':
        current_turn['response'] = msg['content']
        res.append(current_turn)
        current_turn = {}
      # endif role
    # endfor
    return res

  def get_response_hosted(self, user, message):
    user_data = self.__user_data[user]
    # Retrieve the system prompt
    sys_info = user_data.get('system_prompt')
    # Convert previous messages to history, if any
    history = self.__messages_to_history(user_data.get('messages', []))
    data = {
      'request': message,
      'history': history,
      'identity': sys_info
    }
    return self.process_url_request(
      data, url=self.get_request_url_hosted(), error_check_func=self.check_request_error_hosted,
      response_route=self.get_response_route_hosted()
    )


  def get_response(self, user, message):
    agent_type = str(self.cfg_agent_type).lower()
    self.P(f"Agent type: {agent_type}")
    if agent_type == 'api':
      return self.get_response_api(user, message)
    elif agent_type == 'hosted':
      return self.get_response_hosted(user, message)
    return None

  def add_conversation_history(self, user, role, content):
    self.__user_data[user]['messages'].append({"role": role, "content": content})
    return

  def maybe_init_user_data(self, user):
    if user not in self.__user_data:
      self.__user_data[user] = {
        'system_prompt': self.cfg_system_prompt or '',
        'messages': []
      }
    # endif user not in self.__user_data
    return

  def bot_msg_handler(self, message, user, **kwargs):
    if message == '\\reset':
      self.__user_data[user] = {
        'system_prompt': self.cfg_system_prompt or '',
        'messages': []
      }
      return "Conversation history reset."
    # endif conversation is reset
    self.maybe_init_user_data(user)
    self.P(f"Received message from {user}: {message}")
    response = self.get_response(user, message)
    if response is None:
      result = "An error occurred while processing the request."
    else:
      result = response
      self.add_conversation_history(user, role='user', content=message)
      self.add_conversation_history(user, role='assistant', content=response)
    # endif response is not None
    self.P(f"Sending response to {user}: {result}")
    return result
  

  def process(self):
    payload = None
    if (self.time() - self.__last_status_check) > self.cfg_send_status_each:
      self.__last_status_check = self.time()
      if not self.__failed:
        self.bot_dump_stats()
    return payload
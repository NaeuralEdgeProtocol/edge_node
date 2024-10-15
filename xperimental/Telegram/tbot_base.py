import os
import traceback
import datetime
import threading
import time
import asyncio

import telegram
from telegram import Update, Message
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from utils.oaiwrapper import OpenAIApp
from utils.utils import log_with_color


__VERSION__ = '3.1.0'


FULL_DEBUG = False


class TelegramChatbot(object):
  def __init__(
    self, 
    bot_name, 
    token_env_name, 
    persona, 
    log=None, 
    persona_location='./models/personas/'
  ):
    super().__init__()
    
    assert isinstance(bot_name, str), "bot_name must be a string. Provided: {}".format(bot_name)
    
    self.__log = log
    assert isinstance(token_env_name, str), "token_env_name must be a string. Provided: {}".format(token_env_name)
    
    token = os.environ.get(token_env_name)
    assert token is not None, "Token environment variable not found: {}".format(token_env_name)    

    self.__token = token
    self.__bot_name = bot_name
    self.__persona_location = persona_location
    self.__persona = persona
    self.__eng : OpenAIApp = None
    self.__app : Application = None
    
    self.__bot_thread = None
    self.__asyncio_loop = None
    
    self.__build()
    return
     
  def P(self, s, color=None, **kwargs):
    if self.__log is None:
      log_with_color(s, color=color, **kwargs)
    else:
      self.__log.P(s, color=color, **kwargs)
    return
    
    
  def __build(self):
    self.P("Starting up {} '{}' v{}...".format(
      self.__class__.__name__,self.__bot_name, __VERSION__
      ),
    )
    eng = OpenAIApp(
      persona=self.__persona,
      user=None,
      log=self.__log,
      persona_location=self.__persona_location,
    )
    self.__eng = eng
    self.P("Finished initialization of neural engine.", color='g')
    return
    

  def handle_response(self, user: str, text: str) -> str:    
    self.P("  Preparing response for {}...".format(user))    
    # Create your own response logic
    processed: str = text.lower()    
    answer = self.__eng.ask(question=processed, user=str(user))
    return answer    
  
  
  async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    message : Message = update.message
    if message is None:
      return
    
    # Get basic info of the incoming message
    message_type: str = message.chat.type
    text: str = message.text
    bot_name : str = self.__bot_name
    
    chat_id = update.effective_message.chat_id    
    initiator_id = message.from_user.id
    
    if message.from_user.first_name is not None:
      initiator_name = message.from_user.first_name
    else:
      initiator_name = initiator_id

    is_bot_in_text = bot_name in text
    text = text.replace(bot_name , '').strip()
    chat_name = message.chat.title
    
    if FULL_DEBUG:
      self.P(f'User {initiator_name} ({initiator_id}) in `{chat_name}` ({message_type}): "{text}"')
    
    allow = False
    # React to group messages only if users mention the bot directly
    if message_type in ['group', 'supergroup']:
      if is_bot_in_text:
        allow = True
      else:
        reply_to = message.reply_to_message
        if reply_to is not None:
          self.P(f"Reply from '{initiator_name}' to {reply_to.from_user} ")
          if reply_to.from_user.is_bot:
            allow = True
    else:
      chat_name = initiator_name
      allow = True
    
    if not allow:
      return

    if not FULL_DEBUG:
      # Print a log for debugging
      self.P(f'User {initiator_name} ({initiator_id}) in `{chat_name}` ({message_type}): "{text}"')
    

    await context.bot.send_chat_action(chat_id=chat_id, action=telegram.constants.ChatAction.TYPING)
    response: str = self.handle_response(user=initiator_id, text=text)

    # Reply normal if the message is in private
    self.P('  Bot resp: {}'.format(response), color='m')
    await message.reply_text(response)
    return    
    
  
  # Log errors
  async def _on_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    exc = traceback.format_exc()
    msg = (
      f'Update {update} caused error {context.error}\n\n'
      f'Bot:       {context.bot.name} {context.bot.username} {context.bot.first_name} {context.bot.last_name}\n'
      f'Bot data:  {context.bot_data}\n'
      f'Chat data: {context.chat_data}\n'
      f'User data: {context.user_data}\n'
      f'Trace: {exc}'
    )
    self.P(msg, color='r')
    return    
  
  
  def bot_runner(self):    
    self.__app = Application.builder().token(self.__token).build()
    # Commands
    # app.add_handler(CommandHandler('start', start_command))
    # app.add_handler(CommandHandler('help', help_command))
    # app.add_handler(CommandHandler('custom', custom_command))

    # Messages
    self.__app.add_handler(MessageHandler(filters.TEXT, self.handle_message))

    # Log all errors
    self.__app.add_error_handler(self._on_error)

    self.P('Starting polling loop...')

    if self.__running_threaded:
      # Create a new event loop
      self.__asyncio_loop = asyncio.new_event_loop()
      
      # Set this loop as the current event loop for the new thread
      asyncio.set_event_loop(self.__asyncio_loop)
        
      # Start the bot using the new event loop
      try:
        self.__asyncio_loop.run_until_complete(self.__app.run_polling(poll_interval=3))
      except Exception as e:
        self.P(f"Error in bot_runner: {e}", color='r')
      finally:
        # Ensure the loop is closed after polling is done
        self.P("Closing asyncio loop...")
        self.__asyncio_loop.close()
    else:
      self.__app.run_polling(poll_interval=3)
    return 
  
  
  def run_threaded(self):
    self.__running_threaded = True
    obfuscated_token = self.__token[:5] + '...' + self.__token[-5:]
    self.P("Starting bot...")
    self.__bot_thread = threading.Thread(target=self.bot_runner)
    self.__bot_thread.start()
    time.sleep(2)
    self.P("Started {} using {} v{}, token {}...".format(
      self.__bot_name, self.__class__.__name__, __VERSION__, obfuscated_token
      ),
      color='g', boxed=True
    )
    return
  
  def run_blocking(self):
    self.__running_threaded = False
    self.P("Starting bot...")
    self.bot_runner()
    return
    
  def stop(self):
    self.P("Stopping bot...", color='r')
    if self.__asyncio_loop is not None:
      self.P("Stopping asyncio loop...")
      self.__asyncio_loop.stop()
    if self.__bot_thread is not None:
      self.P("Waiting for bot thread to join...")
      self.__bot_thread.join()
    self.P("Bot stopped.", color='g')
    return
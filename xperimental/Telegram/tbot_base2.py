import os
import traceback
import datetime
import threading
import time
import asyncio

import telegram
from telegram import Update, Message
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes


__VERSION__ = '3.1.0'

def log_with_color(message: str, color: str, boxed:bool = False, **kwargs) -> None:
  """
  Log a message with color.

  Args:
    message (str): The message to be logged.
    color (str): The color to be used for logging. Valid color options are "yellow", "red", "gray", "light", and "green".

  Returns:
    None
  """
  color_codes = {
    "y": "\033[93m",
    "r": "\033[91m",
    "gray": "\033[90m",
    "light": "\033[97m",
    "g": "\033[92m",
    "b": "\033[94m",
  }

  if color not in color_codes:
    color = "gray"

  end_color = "\033[0m"
  now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  prefix = f"[{now_str}] "
  
  if boxed:
    indent = 4
    str_indent = ' ' * indent
    spaces = 20
    line0 = '#' * (len(message) + spaces + 2)
    line1 = str_indent + line0
    line2 = str_indent + '#' + ' ' * (len(line0) - 2) + '#'
    line3 = str_indent + '#' + ' ' * (spaces // 2)  + message + ' ' * (spaces // 2) + '#'
    line4 = str_indent + '#' + ' ' * (len(line0) - 2) + '#'
    line5 = line1
    message =  f"{prefix}\n{line1}\n{line2}\n{line3}\n{line4}\n{line5}"
  else:
    message = f"{prefix}{message}"
  
  print(f"{color_codes.get(color, '')}{message}{end_color}", flush=True)
  return



def load_dotenv(filename=".env"):
  """
  Load environment variables from a .env file into the OS environment.

  Parameters
  ----------
  filename : str, optional
      The name of the .env file to load, by default ".env".
  
  Raises
  ------
  FileNotFoundError
      If the specified .env file is not found in the current directory.
  """
  if not os.path.isfile(filename):
    raise FileNotFoundError(f"{filename} not found in the current directory.")

  with open(filename) as f:
    for line in f:
      # Strip whitespace and skip empty lines or comments
      line = line.strip()
      if not line or line.startswith("#"):
        continue
      
      # Parse key-value pairs
      if "=" in line:
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        os.environ[key] = value
  return


class TelegramChatbot(object):
  def __init__(
    self, 
    log, 
    bot_name_env_name="TELEGRAM_BOT_NAME", 
    token_env_name="TELEGRAM_BOT_TOKEN", 
    conversation_handler=None, 
    debug=False,
  ):
    super().__init__()
    
    self.__log = log
    
    self.bot_debug = debug

    assert isinstance(bot_name_env_name, str), "bot_name_env_name must be a string. Provided: {}".format(bot_name_env_name)
    bot_name = os.environ.get(bot_name_env_name)
    assert isinstance(bot_name, str), "bot_name must be a string. Provided: {}".format(bot_name)

    assert isinstance(token_env_name, str), "token_env_name must be a string. Provided: {}".format(token_env_name)    
    token = os.environ.get(token_env_name)
    assert token is not None, "Token environment variable not found: {}".format(token_env_name)    


    self.__token = token
    self.__bot_name = bot_name
    
    self.__eng = conversation_handler
    self.__app : Application = None
    
    self.__bot_thread = None
    self.__asyncio_loop = None
    
    self.__build()
    return
     
  def bot_log(self, s, color=None, low_priority=False, **kwargs):
    if low_priority and not self.bot_debug:
      return
    if self.__log is None:
      log_with_color(s, color=color, **kwargs)
    else:
      self.__log.P(s, color=color, **kwargs)
    return
    
    
  def __build(self):
    self.bot_log("Starting up {} '{}' v{}...".format(
      self.__class__.__name__,self.__bot_name, __VERSION__
      ),
    )
    if hasattr(self.__eng, 'ask'):
      self.bot_log("{} has a conversation handler.".format(self.__eng.__class__.__name__))
    else:
      self.bot_log("No conversation handler found. Using echo mode.")
    self.bot_log("Finished initialization of neural engine.", color='g')
    return
  
  
  def reply_wrapper(self, question, user):
    result = self.__eng.ask(question=question, user=user)
    return result
    

  async def handle_response(self, user: str, text: str) -> str:    
    self.bot_log("  Preparing response for {}...".format(user), low_priority=True)    
    # Create your own response logic
    processed: str = text.lower()
    loop = asyncio.get_running_loop()
    answer = await loop.run_in_executor(
      None,  # Use the default executor (a ThreadPoolExecutor)
      self.__eng.ask,
      processed,
      str(user)
    )
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
    
    if self.bot_debug:
      self.bot_log(
        f'User {initiator_name} ({initiator_id}) in `{chat_name}` ({message_type}): "{text}"',
        low_priority=True
      )
    
    allow = False
    # React to group messages only if users mention the bot directly
    if message_type in ['group', 'supergroup']:
      if is_bot_in_text:
        allow = True
      else:
        reply_to = message.reply_to_message
        if reply_to is not None:
          self.bot_log(f"Reply from '{initiator_name}' to {reply_to.from_user} ", low_priority=True)
          if reply_to.from_user.is_bot:
            allow = True
    else:
      chat_name = initiator_name
      allow = True
    
    if not allow:
      return

    if self.bot_debug:
      # Print a log for debugging
      self.bot_log(
        f'User {initiator_name} ({initiator_id}) in `{chat_name}` ({message_type}): "{text}"',
        low_priority=True
    )
    

    await context.bot.send_chat_action(chat_id=chat_id, action=telegram.constants.ChatAction.TYPING)
    
    # next line is the main logic of the bot
    # TODO: must be converted to async
    response: str = await self.handle_response(user=initiator_id, text=text)

    # Reply normal if the message is in private
    self.bot_log('  Bot resp: {}'.format(response), color='m', low_priority=True)
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
    self.bot_log(msg, color='r')
    return    
  

  def bot_runner(self):
    # Create and set a new event loop for this thread
    self.bot_log("Creating asyncio loop...")
    self.__asyncio_loop = asyncio.new_event_loop()
    self.bot_log("Setting asyncio loop...")
    asyncio.set_event_loop(self.__asyncio_loop)

    # Create an asyncio Event to signal stopping
    self.__stop_event = asyncio.Event()

    try:
      # Run the bot's main coroutine
      self.bot_log("Running bot async loop run_until_complete ...")
      self.__asyncio_loop.run_until_complete(self._run_bot())
      self.bot_log("Bot main coroutine finished.")
    except Exception as e:
      self.bot_log(f"Error in bot_runner: {e}", color='r')
    finally:
      self.bot_log("Closing asyncio loop...")
      # Shutdown asynchronous generators
      self.__asyncio_loop.run_until_complete(self.__asyncio_loop.shutdown_asyncgens())
      # Close the event loop
      self.__asyncio_loop.close()
    
    self.bot_log("Bot runner thread exit.", color='g')
    return
    

  async def _run_bot(self):
    self.__app = Application.builder().token(self.__token).build()

    # Add handlers
    self.__app.add_handler(MessageHandler(filters.TEXT, self.handle_message))
    self.__app.add_error_handler(self._on_error)

    # Initialize and start the bot
    await self.__app.initialize()
    await self.__app.start()
    self.bot_log('Bot started.')

    # Start polling without installing signal handlers
    await self.__app.updater.start_polling(poll_interval=3)

    # Wait until the stop event is set
    await self.__stop_event.wait()

    # Stop the updater and the application
    await self.__app.updater.stop()
    await self.__app.stop()
    await self.__app.shutdown()
    self.bot_log('Bot stopped.')
    return


  def run_threaded(self):
    self.__running_threaded = True
    obfuscated_token = self.__token[:5] + '...' + self.__token[-5:]
    self.bot_log("Starting bot...")
    self.__bot_thread = threading.Thread(target=self.bot_runner)
    self.__bot_thread.start()
    time.sleep(2)
    self.bot_log("Started {} using {} v{}, token {}...".format(
        self.__bot_name, self.__class__.__name__, __VERSION__, obfuscated_token
        ),
        color='g', boxed=True
    )
    return


  def stop(self):
    self.bot_log("Stopping bot...", color='r')
    if self.__asyncio_loop is not None and self.__stop_event is not None:
        self.bot_log("Signaling bot to stop...")
        self.__stop_event.set()
    if self.__bot_thread is not None:
        self.bot_log("Waiting for bot thread to join...")
        self.__bot_thread.join()
    self.bot_log("Bot stopped.", color='g')
    return

  
  def run_blocking(self):
    self.__running_threaded = False
    self.bot_log("Starting bot...")
    self.bot_runner()
    return  
  
  
if __name__ == "__main__":
  
  from naeural_core import Logger
  THREADED_MODE, BLOCKING_MODE = "threaded", "blocking"
  _MODES = [THREADED_MODE, BLOCKING_MODE]
  
  PERSONA_LOCATION = './models/personas/'
  
  FULL_DEBUG = True  
  BOT_MODE = _MODES[0]
  debug_time = 30
  
  
  class FakeAgent:
    def __init__(self, log) -> None:
      self.log = log
      return
        
    def ask(self, question, user):
      if FULL_DEBUG:
        self.log.P("  FakeAgent: Asking question '{}' for user '{}'...".format(question, user))
      return "Answer for {} is the question itself: {}".format(user, question)  
  
  
  l = Logger("TBOT", base_folder=".", app_folder="_local_cache")
  load_dotenv()
  
  l.P("Preparing conversation handler...", color='b')
  try:
    from xperimental.Telegram.oaiwrapper import OpenAIApp
    eng = OpenAIApp(
      persona='', 
      log=l,
      persona_location=PERSONA_LOCATION,
    )
  except Exception as e:
    l.P(f"Error preparing conversation handler: {e}", color='r')
    eng = FakeAgent(log=l)
  
  l.P("Starting Telegram Bot...", color='b')
  bot = TelegramChatbot(
    log=l,
    conversation_handler=eng,  
    debug=FULL_DEBUG,  
  )
  
  l.P("Running bot in {} mode...".format(BOT_MODE), color='b') 
  
  if BOT_MODE == BLOCKING_MODE:
    bot.run_blocking()
  elif BOT_MODE == THREADED_MODE:
    bot.run_threaded()
    start_time = time.time()
    done = False
    ping_interval = 10
    interval_start = time.time()
    while not done:
      time.sleep(1)
      if time.time() - interval_start > ping_interval:
        bot.bot_log("MAIN: Ping from main thread", color='b')
        interval_start = time.time()
      elapsed = time.time() - start_time
      if elapsed > debug_time:
        bot.bot_log("MAIN: DEBUG_TIME elapsed. Exiting.", color='r')
        done = True
    bot.stop()
    bot.bot_log("MAIN: System shutdown complete.", color='g')
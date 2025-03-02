import traceback
import threading
import time
import asyncio
import json

import telegram
from telegram import Update, Message
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes



__VERSION__ = '4.0.3'


class _TelegramChatbotMixin(object):
  
  def __add_user_info(self, user, question):
    if user not in self.__stats:
      self.__stats[user] = {
        'questions': 0,
        'last_question': None,
        # 'last_answer': None,
      }
    self.__stats[user]['questions'] += 1
    self.__stats[user]['last_question'] = question
    return     


  def _create_tbot_loop_processing_handler(self, str_base64_code, lst_arguments):
    if str_base64_code is None:
      self.P("No loop processing handler provided, skipping...", color='y')
      self._processing_handler = None
    else:
      self.P(f"Preparing custom loop processing handler with arguments: {lst_arguments}...")    
      self._tbot_loop_processing_handler, errors, warnings = self._get_method_from_custom_code(
        str_b64code=str_base64_code,
        self_var='plugin',
        method_arguments=['plugin'] + lst_arguments,
        
        debug=True,
      )
    return  
  
  def maybe_process_tbot_loop(self):
    if getattr(self, "_tbot_loop_processing_handler", None) is not None:
      result = self._tbot_loop_processing_handler(plugin=self)
      if result is not None:
        if isinstance(result, dict):
          self.add_payload_by_fields(**result)
        else:
          self.add_payload_by_fields(result=result)
      # endif result is not None
    # endif _tbot_loop_processing_handler is not None
    return
    
  def __reply_wrapper(self, question, user):
    self.__add_user_info(user=user, question=question)
    result = self.__message_handler(message=question, user=user)
    return result
    

  async def __handle_response(self, user: str, text: str) -> str:    
    self.bot_log("  Preparing response for {}...".format(user), low_priority=True)    
    # Create your own response logic
    question: str = text.lower()
    usr =  str(user).lower()
    loop = asyncio.get_running_loop()
    answer = await loop.run_in_executor(
      None,  # Use the default executor (a ThreadPoolExecutor)
      self.__reply_wrapper,
      question,
      usr
    )
    return answer    
  
  
  async def __handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    response: str = await self.__handle_response(user=initiator_id, text=text)

    # Reply normal if the message is in private
    self.bot_log('  Bot resp: {}'.format(response), color='m', low_priority=True)    
    await message.reply_text(response)
    if self.bot_debug:
      self.bot_dump_stats()
    return    
    
  
  # Log errors
  async def __on_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
  

  def __bot_runner(self):
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
      self.__asyncio_loop.run_until_complete(self.__run_bot())
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
    

  async def __run_bot(self):
    self.__app = Application.builder().token(self.__token).build()

    # Add handlers
    self.__app.add_handler(MessageHandler(filters.TEXT, self.__handle_message))
    self.__app.add_error_handler(self.__on_error)

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


  def __run_threaded(self):
    self.__running_threaded = True
    obfuscated_token = self.__token[:5] + '...' + self.__token[-5:]
    self.bot_log("Starting bot...")
    self.__bot_thread = threading.Thread(target=self.__bot_runner)
    self.__bot_thread.start()
    time.sleep(2)
    self.bot_log("Started {} using {} v{}, token {}...".format(
        self.__bot_name, self.__class__.__name__, __VERSION__, obfuscated_token
        ),
        color='g', boxed=True
    )
    return


  
  def __run_blocking(self):
    self.__running_threaded = False
    self.bot_log("Starting bot...")
    self.bot_runner()
    return  
  
  
  ## Public methods
  
  def bot_dump_stats(self):
    self.bot_log("Bot stats:\n{}".format(json.dumps(self.__stats, indent=2)))
    return
  
  def bot_stop(self):
    self.bot_log("Stopping bot...", color='r')
    if self.__asyncio_loop is not None and self.__stop_event is not None:
      self.bot_log("Signaling bot to stop...")
      self.__stop_event.set()
    if self.__bot_thread is not None:
      self.bot_log("Waiting for bot thread to join...")
      self.__bot_thread.join()
    self.bot_log("Bot stopped.", color='g')
    return

  
  
  def bot_run(self):
    if self.__running_threaded:
      self.__run_threaded()
    else:
      self.__run_blocking()
    return
  
 
  def bot_log(self, s, color=None, low_priority=False, **kwargs):
    if low_priority and not self.bot_debug:
      return
    self.P(s, color=color, **kwargs)
    return
    
    
  def bot_build(
    self, 
    token, 
    bot_name, 
    message_handler, 
    run_threaded=True, 
    bot_debug=False
  ):
    """
    Builds a Telegram bot with the given token and name.
    
    Parameters:
    ----------
    
    token : str
      The token of the bot.
      
    bot_name : str
      The name of the bot.
      
    messge_handler : function
      The function that will handle the messages having the following signature: 
      `message_handler(message: str, user: str) -> str`
    
    run_threaded : bool
      If True, the bot will run in a separate thread as it is recommended in the plugin system.    
    
    """
    self.__app : Application = None    
    self.__bot_thread = None
    self.__asyncio_loop = None
    self.__stats = {}
    self.bot_debug = bot_debug
    self.__token = token
    self.__bot_name = bot_name
    self.__message_handler = message_handler
    
    self.bot_runner_version = __VERSION__
    self.__running_threaded = run_threaded
    
    
    self.bot_log("Starting up {} '{}' v{}...".format(
      self.__class__.__name__,self.__bot_name, __VERSION__
      ), color='g', boxed=True
    )
    return
  
  def on_close(self):
    self.P("Initiating bot shutdown procedure...")
    self.bot_stop()
    return
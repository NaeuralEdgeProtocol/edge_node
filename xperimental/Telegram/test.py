import time

from xperimental.Telegram.oaiwrapper import OpenAIApp
from xperimental.Telegram.tbot_base import TelegramChatbot
from xperimental.Telegram.utils import load_dotenv, FakeAgent
from naeural_core import Logger
 
if __name__ == "__main__":
  
  
  THREADED_MODE, BLOCKING_MODE = "threaded", "blocking"
  _MODES = [THREADED_MODE, BLOCKING_MODE]
  
  PERSONA_LOCATION = './models/personas/'
  
  FULL_DEBUG = True  
  BOT_MODE = _MODES[0]
  debug_time = 30
  
  l = Logger("TBOT", base_folder=".", app_folder="_local_cache")
  load_dotenv()
  
  l.P("Preparing conversation handler...", color='b')
  try:
    
    eng = OpenAIApp(
      persona='', 
      log=l,
      persona_location=PERSONA_LOCATION,
    )
  except Exception as e:
    l.P(f"Error preparing conversation handler: {e}", color='r')
    eng = FakeAgent(log=l, bot_debug=FULL_DEBUG)
  
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
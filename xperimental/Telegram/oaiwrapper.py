"""
Copyright (C) 2017-2021 Andrei Damian, andrei.damian@me.com,  All rights reserved.

This software and its associated documentation are the exclusive property of the creator. 
Unauthorized use, copying, or distribution of this software, or any portion thereof, 
is strictly prohibited.


Dissemination of this information or reproduction of this material is strictly forbidden unless prior 
written permission from the author.

"""

import os
import requests
import json
import traceback
import datetime
from utils.utils import log_with_color

_FOLDER = './personas'

DIRECT_USER = 'direct-user'

class OpenAIApp(object):
  def __init__(
    self, 
    persona, 
    user=None, 
    log=None, 
    persona_location=None,
    debug_mode=False,
  ):
    assert isinstance(persona, str), "`Persona` must be a string"
    if persona_location is None:
      persona_location = _FOLDER
    self.__persona_location = persona_location
    self.log = log
    self.data = {}
    self.debug_mode = debug_mode
    self.persona = persona.lower()
    if user is not None:
      user = user.lower()
    self.user = user
    self.load_persona()
    return
  
  def P(self, s, color=None, boxed=False):
    if self.log is None:
      log_with_color(s, color=color, boxed=boxed)
    else:
      self.log.P(s, color=color, boxed=boxed)
    return
  
  
  def list_models(self):
    url = 'https://api.openai.com/v1/models'
    res = self.request(data=None, url=url, content_path=['data'], method='GET')    
    return res
    
  
  def _get_empty_data(self, key=None, model=None, user=None, init=None, functions=None, function_call=None):
    if user is None:
      if self.user is None:
        raise ValueError("_get_empty_data without specific USER on a user-less chat engine")
      else:
        user = self.user
    user = user.lower()
      
    if init is None:
      init = self._init
    if key is None:
      key = self._key
    if model is None:
      model = self._model
    if self._is_chatbot:
      data = {
        "model" : self._model,
        "user"  : user,
        "messages" : []
      }
      if init is not None:
        data['messages'].append({"role" : "system", "content" : init})
    else:
      data = {
        "model" : self._model,
      }
    
    if functions is not None:
      data.update({"functions": functions})
    if function_call is not None:
      data.update({"function_call": function_call})
    return data  
  
  
  def _add_message(self, content, user=None, role='user', data=None):
    if data is None:
      if user is None:
        if self.user is None:
          raise ValueError("_add_message without specific USER/data on a user-less chat engine")
        else:
          user = self.user      
      user = user.lower()        
      if user not in self.data:
        self.reset(user=user)
      data = self.data[user]      
    if self._is_chatbot:
      turn = {"role" : role, "content" : content}
      data['messages'].append(turn)
    else:
      data = {
        "model" : self._model,
        "prompt": content,
      }      
    data = {
      **self._params,
      **data,
    }
    if self.debug_mode:
      if role == 'user':
        self.P("[GPT] New turn: User({}) '{}'".format(user, content))
      else:
        self.P("[GPT]  Assistant: {}".format(content))
    return data
  
  
  def request(self, data, debug=False, url=None, content_path=None, method='POST'):
    if url is None:
      url = self._url
    if content_path is None:
      content_path = self._content_path
    response = None
    result = None
    try:    
      if method.upper() == 'POST':
        func = requests.post
      else:
        func = requests.get
      response = func(
        url,
        headers={
          "Content-Type": "application/json", 
          "Authorization": "Bearer {}".format(self._key)
        },
        json=data,
      )
      response = response.json()
      result = response
      for path in content_path:
        result = result[path]      
      if debug:
        print("{}: {}".format(self.__class__.__name__, response))
    except Exception as exc:
      raise ValueError("Request failed with '{}', reponse: {}".format(exc, response))
    return result

    
  def ask(self, question, user=None, debug=False):
    if user is None:
      user = self.user
      if self.user is None:
        raise ValueError("ask-ed a question without specific USER on a user-less chat engine")
    user = user.lower()
    
    self._add_message(question, user=user, role='user')
    data = self.data[user]
    result = self.request(data, debug=debug)
    if result is not None:
      self._add_message(result, user=user, role='assistant')
    return result
  
  
  def ask_direct(self, question, debug=False):
    self.reset(user=DIRECT_USER)
    data = self._add_message(question, user=DIRECT_USER)
    result = self.request(data, debug=False)
    return result


  def load_persona(self, persona=None, user=DIRECT_USER):
    if persona is None:
      persona = self.persona
    found = False
    persona = persona.replace('.json', '')
    fn = os.path.join(self.__persona_location, persona + '.json')
    self.P("Trying to load '{}'...".format(fn))
    found = os.path.isfile(fn)
    if not found:
      fn = os.path.join(self.__persona_location, persona)
      self.P("Trying to load '{}'...".format(fn))
      found = os.path.isfile(fn)
          
    assert found, "Unknown chatbot persona '{}'".format(persona)
    
    with open(fn, "rt") as fh:
      _data = json.load(fh)
    
    self._key = _data['api_key']
    if self._key is None:
      self._key = os.environ['GPT_KEY']
    obfuscated_key = self._key[:5] + '...' + self._key[-5:]
    msg = "Started {} with key: {}".format(self.__class__.__name__, obfuscated_key)
    self._init = _data.get('init')
    if self._init is None:
      self.P("Trying to load init info from '{}'...".format(fn))
      p_fn = os.path.join(self.__persona_location, persona + "_init.txt")
      with open(p_fn, "rt") as fh:
        self._init = fh.read()
    
    self._url = _data['url']
    self._model = _data['model']
    self._content_path = _data['content_path']
    self._is_chatbot = _data['is_chat']
    self._params = _data.get('params', {})
    self._functions = _data.get('functions')
    self._function_call = _data.get('function_call')
    self.reset(functions=self._functions, function_call=self._function_call, user=user)
    self.P(msg, color='g', boxed=True)
    return


  def reset(self, key=None, user=None, init=None, model=None, functions=None, function_call=None):
    if user is None:
      user = self.user
      if user is None:
        raise ValueError("Reset received without specific USER on a user-less chat engine")

    user = user.lower()
    self.data[user] = self._get_empty_data(
      key=key, 
      model=model, 
      init=init, 
      user=user,
      functions=functions, 
      function_call=function_call,
    )
    return
  
  
  
if __name__ == '__main__':
  MOTION_TEST = True
  DATA_TEST = False
  if MOTION_TEST:
    TESTS = ['Ce face aplicatia voastra?', "cum pot sa bluerz un film?", "Tu esti Skynet?"]
    id_test = 0
    eng = OpenAIApp(persona='Motionmask', user='Andrei')
    done = False
    while not done:
      if TESTS is not None and id_test < len(TESTS):
        inp = TESTS[id_test]
        id_test += 1
      else:
        inp = input(">")
      if inp.lower() in ['exit', 'pa', 'close', "la revedere", 'end']:
        done = True
      if not done:
        resp = eng.ask(inp)
        print("\n")
        print(resp)
        
  if DATA_TEST:
    query = 'Please generate in json format quizes where the answer is single word and completes the question. Propose another 4 wrong asnwers. Thematic is elementary school math. The questions should be amusing. Simplify the json format such as the "question" is "q", "correct_answer" is "a", "wrong_answers" is "wa" and the language "l":"en" or "l":"ro". Write the json puting each object in one line with the keys in the following order: "l", "q", "a", "wa" and end the line with a comma. Generate a total of 50 quizes for Romanian language'
    eng = OpenAIApp(persona="Worker", user='Andrei')
    res = eng.ask_direct(query)
    print(res)
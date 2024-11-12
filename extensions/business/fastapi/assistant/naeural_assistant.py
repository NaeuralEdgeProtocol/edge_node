from naeural_core.business.default.web_app.naeural_fast_api_web_app import NaeuralFastApiWebApp as BasePlugin
import pickle


_CONFIG = {
  **BasePlugin.CONFIG,
  'USE_NGROK': False,
  'NGROK_ENABLED': False,
  'NGROK_DOMAIN': None,
  'NGROK_EDGE_LABEL': None,

  'REQUEST_TIMEOUT': 60,
  'PROCESS_DELAY': 0,
  "TEMPLATE_SYS_INFO": {},
  'PORT': 5004,
  "JINJA_ARGS": {
    'html_files': [
      {
        'name': 'index.html',
        'route': '/',
        'method': 'get'
      }
    ]
  },
  'ASSETS': 'extensions/business/fastapi/assistant',
  'VALIDATION_RULES': {
    **BasePlugin.CONFIG['VALIDATION_RULES'],
    'TEMPLATE_SYS_INFO': {
      'TYPE': 'dict',
      'DESCRIPTION': 'The system info templates. The keys are the aliases.'
                     'If a path is provided the system info will be loaded from the file.'
                     'The given file should be a .pkl with the base64 encoded system info.',
    }
  },
}


class NaeuralAssistantPlugin(BasePlugin):
  CONFIG = _CONFIG

  def __init__(self, **kwargs):
    self.conversation_data = {}
    self.template_sys_info = {}
    super(NaeuralAssistantPlugin, self).__init__(**kwargs)
    return

  def load_template_sys_info(self, sys_path):
    pkl_full_path = self.os_path.abspath(sys_path)
    self.P(f'Loading system info from {sys_path} | {pkl_full_path}')
    with open(sys_path, 'rb') as f:
      sys_info_pkl_base64 = pickle.load(f)
    return bytes.fromhex(sys_info_pkl_base64).decode('utf-8')

  def on_init(self):
    super(NaeuralAssistantPlugin, self).on_init()
    # TODO: same procedure if cfg_template_sys_info is changed
    paths_dict = self.cfg_template_sys_info or {}
    # Loading the templates for system info
    for key, sys_info in paths_dict.items():
      if self.os_path.exists(sys_info):
        sys_info = self.load_template_sys_info(sys_path=sys_info)
      # endif path provided
      self.template_sys_info[str(key).lower()] = sys_info
    # endfor templates for system info
    self.P(f"Loaded system info templates: {self.json_dumps(self.shorten_str(self.template_sys_info), indent=2)}")
    return

  def webapp_get_persistence_data_object(self):
    return {
      'conversation_data': self.conversation_data
    }

  def webapp_load_persistence_data_object(self, data):
    saved_conversation_data = data.get('conversation_data', {})
    self.conversation_data = {
      **saved_conversation_data,
      **self.conversation_data
    }
    return

  def relevant_plugin_signatures_llm(self):
    return ['llm_agent', 'code_assist_01', 'ro_llama_agent']

  def relevant_plugin_signatures_embedding(self):
    return ['doc_embedding_agent']

  def relevant_plugin_signatures(self):
    return self.relevant_plugin_signatures_llm() + self.relevant_plugin_signatures_embedding()

  def get_relevant_plugin_signatures(self, agent_type='llm'):
    if agent_type == 'llm':
      return self.relevant_plugin_signatures_llm()
    elif agent_type == 'embedding':
      return self.relevant_plugin_signatures_embedding()
    return []

  def process_response_payload(self, payload_data):
    processed_data = {k.lower(): v for k, v in payload_data.items()}
    text_responses = processed_data.get('text_responses', [])
    response = text_responses[0] if len(text_responses) > 0 else ""
    inferences = processed_data.get('inferences', [])
    tps_lst = [x['tps'] for x in inferences]
    tps = self.np.mean(tps_lst) if len(tps_lst) > 0 else 0.0
    return {
      # 'request_id': processed_data.get('request_id', None),
      # 'text_responses': processed_data.get('text_responses', []),
      'text_response': response,
      'tps': tps,
      # 'inferences': processed_data.get('inferences', []),
      'serving_node_id': processed_data.get('ee_id', None),
      'serving_node_address': processed_data.get('ee_sender', None),
      'web_node_address': self.node_addr,
      'web_node_id': self.node_id,
      'llm_plugin_signature': processed_data.get('signature'),
      'ai_engine': processed_data.get('_p_graph_type'),
      'model_name': processed_data.get('model_name'),
    }

  def get_agent_pipelines(self, node_addr, agent_type='llm'):
    """
    Here, given a node, a list of all the pipelines containing an LLM agent is returned.
    Parameters
    ----------
    node_addr : str - the node address
    agent_type : str - the type of agent to look for

    Returns
    -------
    pipelines : list[Pipeline] - a list of pipelines containing an LLM agent
    """
    res = []
    # TODO: replace with self.netmon.network_node_pipelines(node_addr) after possible refactoring
    lst_active = self.session.get_active_pipelines(node_addr)
    relevant_signatures = self.get_relevant_plugin_signatures(agent_type=agent_type)
    for pipeline_id, pipeline in lst_active.items():
      plugin_instances = pipeline.lst_plugin_instances
      found = False
      for instance in plugin_instances:
        if instance.signature.lower() in relevant_signatures:
          found = True
        # endif relevant plugin
      # endfor instance
      if found:
        res.append(pipeline)
      # endif found
    # endfor pipeline
    return res

  def get_allowed_agents(self, agent_type='llm'):
    """
    Parameters
    ----------
    agent_type : str - the type of agent to look for

    Returns
    -------
    node_ids : list[str] - a list of node ids that are allowed to process the requests of the specified type.
    """
    lst_allowed = self.session.get_allowed_nodes()
    # TODO: check why the following line produces a different result than the one above.
    # lst_allowed = self.netmon.accessible_nodes
    self.P(f"Allowed nodes: {lst_allowed}")
    lst_online_agents = [self.get_agent_pipelines(x, agent_type=agent_type) for x in lst_allowed]
    lst_online_agents = sum(lst_online_agents, [])
    # This may also need refactoring after switching to netmon API
    self.P(f"Online agents: {[(x.node_addr, x.name) for x in lst_online_agents]}")
    return lst_online_agents

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
    return self.template_sys_info.get(str(system_info).lower(), system_info) or ""

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
    history = body.get('history', [])
    system_info = body.get('system_info', "")
    req = body.get('request', "")
    to_send = {
      "STRUCT_DATA": [{
        "request": req,
        "history": history,
        "system_info": self.process_sys_info(system_info),
        'request_id': request_id
      }]
    }
    return to_send

  def compute_request_body_embedding(self, request_id, body):
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
    text = body.get('text', "")
    to_send = {
      "STRUCT_DATA": [{
        "text": text,
        'request_id': request_id
      }]
    }
    return to_send

  def compute_request_body(self, request_id, body, request_type):
    """
    Compute the request body to be sent to the agent's pipeline.
    Parameters
    ----------
    request_id : str - the request id
    body : dict - the request body
    request_type : str - the type of agent to send the request to

    Returns
    -------
    to_send : dict - the request body to be sent to the agent's pipeline
    """
    if request_type == 'llm':
      return self.compute_request_body_llm(request_id, body)
    elif request_type == 'embedding':
      return self.compute_request_body_embedding(request_id, body)

  def send_network_request(self, request_id, pipeline, body, request_type, **kwargs):
    """
    Send a request to the agent's pipeline.
    Parameters
    ----------
    request_id : str - the request id
    pipeline : Pipeline - the pipeline containing the desired agent
    body : dict - the request body
    request_type : str - the type of agent to send the request to
    kwargs : dict - additional keyword arguments

    Returns
    -------

    """
    to_send = self.compute_request_body(request_id, body, request_type=request_type)
    # Maybe refactor after switching to netmon API
    pipeline.send_pipeline_command(to_send, wait_confirmation=False)
    return

  def solve_postponed_request(self, request_id):
    """
    Solve a postponed request.
    Parameters
    ----------
    request_id : str - the request id

    Returns
    -------
    res : dict - the response data
    """
    res = self.maybe_get_network_response(request_id=request_id)
    if res is not None:
      conversation_id = self.requests_meta.get(request_id, {}).get('conversation_id', None)
      if conversation_id is not None:
        self.P(f"Conversation id: {conversation_id} attempting to answer.")
        res['conversation_id'] = conversation_id
        if conversation_id in self.conversation_data:
          req_error = res.get('error', None)
          if req_error is None:
            body = self.requests_meta[request_id]['body']
            request = body.get('request', "")
            response = res.get('text_response', "")
            self.conversation_data[conversation_id]['history'].append({
              'request': request,
              'response': response
            })
          # endif request success
        # endif conversation exists
      # conversation_id available
      return res
    # endif response available
    return self.create_postponed_request(
      solver_method=self.solve_postponed_request,
      method_kwargs={
        'request_id': request_id
      }
    )

  def process_request(self, body, request_type: str = 'llm', conversation_id: str = None):
    request_id = self.uuid()
    lst_online_agents = self.get_allowed_agents(agent_type=request_type)
    if len(lst_online_agents) == 0:
      needed_signatures = self.get_relevant_plugin_signatures(agent_type=request_type)
      return {
        'success': False,
        'error': f'No {request_type.upper()} agents({needed_signatures}) are online. Please try again later.'
      }
    # endif no online agents
    # Maybe refactor after switching to netmon API
    pipeline = self.np.random.choice(lst_online_agents)
    self.register_network_request(
      request_id=request_id,
      pipeline=pipeline,
      request_type=request_type,
      body=body,
      timeout=self.cfg_request_timeout,
      conversation_id=conversation_id
    )
    return self.solve_postponed_request(request_id)

  @BasePlugin.endpoint(method='post')
  def llm_request(self, history: list = [], identity: str = "", request: str = ""):
    """
    The request will be sent to the LLM agent.
    This works as a stateless API where the conversation history is not stored.
    Parameters
    ----------
    history : list - the conversation history.
    identity : str - the identity of the assistant that will handle this request.
    request : str - the request.

    Returns
    -------

    """
    return self.process_request(
      body={
        'history': history,
        'system_info': identity,
        'request': request
      },
      request_type='llm'
    )

  @BasePlugin.endpoint(method='post')
  def conversation_request(self, conversation_id: str, request: str = ""):
    """
    The request will be sent to the LLM agent.
    This works as a stateful API where the conversation history is stored.
    Parameters
    ----------
    conversation_id : str - the conversation id
    request : str - the request

    Returns
    -------

    """
    if conversation_id not in self.conversation_data:
      return {
        'success': False,
        'error': f'Conversation with id {conversation_id} not found.'
      }
    # endif conversation not found
    conversation_data = self.conversation_data[conversation_id]
    history = conversation_data.get('history', [])
    system_info = conversation_data.get('system_info', "")
    return self.process_request(
      body={
        'history': history,
        'system_info': system_info,
        'request': request
      },
      request_type='llm',
      conversation_id=conversation_id
    )

  # @BasePlugin.endpoint(method='post')
  # def embedding_request(self, text: str = ""):
  #   return self.process_request(
  #     body={
  #       'text': text
  #     },
  #     request_type='embedding'
  #   )

  @BasePlugin.endpoint(method='post')
  def conversation_start(self, identity: str = None):
    """
    The conversation will be given a unique id that will be used to identify it for any request.
    In addition, the conversation data will be stored in the conversation_data dictionary.
    TODO: implement Doc Embedding for the conversations.
     A DocEmbedding agent should be used to store knowledge base for multiple conversations.
    Parameters
    ----------
    identity : str - the identity of the assistant that will handle this conversation.
      This can be used to load a specific identity template for the conversation or a custom identity.
    Returns
    -------

    """
    conversation_id = self.uuid()
    self.conversation_data[conversation_id] = {
      'history': [],
      'system_info': identity
    }
    return {'conversation_id': conversation_id}






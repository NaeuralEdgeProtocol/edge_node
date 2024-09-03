from PyE2 import Payload, Session

from core.business.default.web_app.fast_api_web_app import FastApiWebAppPlugin as BasePlugin

__VER__ = '0.1.0.0'

_CONFIG = {
  **BasePlugin.CONFIG,
  'USE_NGROK': False,
  'NGROK_ENABLED': False,
  'NGROK_DOMAIN': None,
  'NGROK_EDGE_LABEL': None,

  'REQUEST_TIMEOUT': 30,

  'PORT': 5000,
  'ASSETS': '_naeural_assistant',
  'VALIDATION_RULES': {
    **BasePlugin.CONFIG['VALIDATION_RULES'],
  },
}


RELEVANT_PLUGIN_SIGNATURES = [
  'llm_agent',
  'code_assist_01'
]


class NaeuralAssistantPlugin(BasePlugin):
  CONFIG = _CONFIG

  def __init__(self, **kwargs):
    super(NaeuralAssistantPlugin, self).__init__(**kwargs)
    self.requests_responses = {}
    # !!!This approach, although works, will not be allowed in the future because it's not safe
    self.session = Session(
      name=f'{self.str_unique_identification}',
      config=self.global_shmem['config_communication']['PARAMS'],
      log=self.log,
      bc_engine=self.global_shmem[self.ct.BLOCKCHAIN_MANAGER],
      on_payload=self.on_payload,
    )
    return

  def on_init(self):
    super(NaeuralAssistantPlugin, self).on_init()
    return

  def payload_data_to_response_data(self, data):
    processed_data = {k.lower(): v for k, v in data.items()}
    return {
      'request_id': processed_data.get('request_id', None),
      'text_responses': processed_data.get('text_responses', []),
      'inferences': processed_data.get('inferences', []),
      'node_id': processed_data.get('ee_id', None),
      'node_address': processed_data.get('ee_sender', None),
      'web_agent_address': self.node_addr,
      'web_agent_id': self.node_id,
      'llm_plugin_signature': processed_data.get('signature'),
      'ai_engine': processed_data.get('_p_graph_type'),
      'model_name': processed_data.get('model_name'),
    }

  def on_payload(self, sess: Session, node_id: str, pipeline: str, signature: str, instance: str, payload: Payload):
    if signature.lower() not in RELEVANT_PLUGIN_SIGNATURES:
      return
    data = payload.data
    request_id = data.get('REQUEST_ID', None)
    self.requests_responses[request_id] = self.payload_data_to_response_data(data)
    return

  def get_llm_agent_pipelines(self, node_id):
    """
    Here, given a node, a list of all the pipelines containing an LLM agent is returned.
    Parameters
    ----------
    node_id : str - the node id

    Returns
    -------
    pipelines : list[Pipeline] - a list of pipelines containing an LLM agent
    """
    res = []
    lst_active = self.session.get_active_pipelines(node_id)
    for pipeline_id, pipeline in lst_active.items():
      plugin_instances = pipeline.lst_plugin_instances
      found = False
      for instance in plugin_instances:
        if instance.signature.lower() in RELEVANT_PLUGIN_SIGNATURES:
          found = True
        # endif relevant plugin
      # endfor instance
      if found:
        res.append(pipeline)
      # endif found
    # endfor pipeline
    return res

  def get_allowed_agents(self):
    """
    Returns a list of node ids that are allowed to process the requests.
    """
    lst_allowed = self.session.get_allowed_nodes()
    self.P(f"Allowed nodes: {lst_allowed}")
    lst_online_agents = [self.get_llm_agent_pipelines(x) for x in lst_allowed]
    lst_online_agents = sum(lst_online_agents, [])
    self.P(f"Online agents: {[(x.node_addr, x.name) for x in lst_online_agents]}")
    return lst_online_agents

  def send_request(self, request_id, pipeline, body):
    """
    Send a request to the LLM agent's pipeline.
    Parameters
    ----------
    request_id : str - the request id
    pipeline : Pipeline - the pipeline containing the LLM agent
    body : dict - the request body

    Returns
    -------

    """
    history = body.get('history', [])
    system_info = body.get('system_info', "")
    req = body.get('request', "")
    to_send = {
      "STRUCT_DATA": [{
        "request": req,
        "history": history,
        "system_info": system_info,
        'request_id': request_id
      }]
    }
    pipeline.send_pipeline_command(to_send, wait_confirmation=False)
    return

  def process_request(self, body):
    request_id = self.uuid()
    lst_online_agents = self.get_allowed_agents()
    if len(lst_online_agents) == 0:
      return False, {'error': 'No LLM agents are online. Please try again later.'}
    # endif no online agents
    pipeline = self.np.random.choice(lst_online_agents)
    self.send_request(request_id, pipeline, body)
    request_ts = self.time()
    while self.time() - request_ts < self.cfg_request_timeout and request_id not in self.requests_responses:
      self.sleep(0.1)
    # endwhile waiting for response
    if request_id not in self.requests_responses:
      return False, {'error': 'Request timeout. Please try again later.'}
    # endif request timeout
    res = self.requests_responses.pop(request_id)
    return True, res

  @BasePlugin.endpoint(method='post')
  def request(self, body):
    success, response_dict = self.process_request(body)
    return {
      'success': success,
      **response_dict
    }


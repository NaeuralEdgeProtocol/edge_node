from core.business.base.cv_plugin_executor import CVPluginExecutor as BasePlugin


_CONFIG = {
  **BasePlugin.CONFIG,

  'AI_ENGINE': 'custom_second_stage_detector',
  'OBJECT_TYPE': [],
  'OBJECTIVE_NAME': None,
  'DESCRIPTION': None,
  'SECOND_STAGE_DETECTOR_CLASSES': [],

  'STARTUP_AI_ENGINE_PARAMS': {
    'CUSTOM_DOWNLOADABLE_MODEL_URL': None,
    'MODEL_INSTANCE_ID': None,
  },
  'ALLOW_EMPTY_INPUTS': True,

  'VALIDATION_RULES': {
    **BasePlugin.CONFIG['VALIDATION_RULES'],
  }
}


class Ai4eCustomInferenceAgentPlugin(BasePlugin):

  def validate_ai_engine_params(self):
    ai_engine_params = self.cfg_startup_ai_engine_params
    err_msg = (f'"STARTUP_AI_ENGINE_PARAMS" should always be a dictionary that contains the following'
               f'2 keys: "CUSTOM_DOWNLOADABLE_MODEL_URL" and "MODEL_INSTANCE_ID".')
    if not isinstance(ai_engine_params, dict):
      self.add_error(err_msg)
    else:
      model_url = ai_engine_params.get('CUSTOM_DOWNLOADABLE_MODEL_URL')
      if model_url is None:
        self.add_error(f'"CUSTOM_DOWNLOADABLE_MODEL_URL" parameter from "STARTUP_AI_ENGINE_PARAMS" should not be None!')
      model_id = ai_engine_params.get('MODEL_INSTANCE_ID')
      if model_id is None:
        self.add_error(f'"MODEL_INSTANCE_ID" parameter from "STARTUP_AI_ENGINE_PARAMS" should not be None!')
    # endif ai_engine_params is dict
    return

  def validate_second_stage_classes(self):
    classes = self.cfg_second_stage_detector_classes
    if not isinstance(classes, list):
      self.add_error(f'"SECOND_STAGE_DETECTOR_CLASSES" parameter should be a list. It instead is {type(classes)}!')
    elif len(classes) < 2:
      self.add_error(f'"SECOND_STAGE_DETECTOR_CLASSES" parameter should have at least 2 elements!')
    # endif
    return

  @property
  def model_key(self):
    return self.cfg_startup_ai_engine_params['MODEL_INSTANCE_ID']

  @property
  def custom_model_url(self):
    return self.cfg_startup_ai_engine_params['CUSTOM_DOWNLOADABLE_MODEL_URL']

  def register_response(self, request_id, response):
    self.lock_resource('CUSTOM_MODELS_REQUESTS_DATA')
    if 'CUSTOM_MODELS_REQUESTS_DATA' not in self.plugins_shmem:
      self.plugins_shmem['CUSTOM_MODELS_REQUESTS_DATA'] = {}
    self.plugins_shmem['CUSTOM_MODELS_REQUESTS_DATA'][request_id] = response
    self.unlock_resource('CUSTOM_MODELS_REQUESTS_DATA')
    return

  def register_ping(self):
    model_id = self.get_instance_id()
    model_data = {
      'TIMESTAMP': self.time(),
      'MODEL_ID': model_id,
      'CONFIG': {
        'INSTANCE_ID': model_id,
        'AI_ENGINE': self.cfg_ai_engine,
        'OBJECT_TYPE': self.cfg_object_type,
        'SECOND_STAGE_DETECTOR_CLASSES': self.cfg_second_stage_detector_classes,
        'STARTUP_AI_ENGINE_PARAMS': {
          'CUSTOM_DOWNLOADABLE_MODEL_URL': self.custom_model_url,
          'MODEL_INSTANCE_ID': self.model_key
        },
        "DESCRIPTION": self.cfg_description,
        "OBJECTIVE_NAME": self.cfg_objective_name,
      },
      'MODEL_NAME': self.cfg_objective_name,
      'MODEL_DESCRIPTION': self.cfg_description,
    }
    self.lock_resource('CUSTOM_MODELS_DATA')
    if 'CUSTOM_MODELS_DATA' not in self.plugins_shmem:
      self.plugins_shmem['CUSTOM_MODELS_DATA'] = {}
    # endif CUSTOM_MODELS_DATA not initialized
    self.plugins_shmem['CUSTOM_MODELS_DATA'][model_id] = model_data
    self.unlock_resource('CUSTOM_MODELS_DATA')
    return

  def _process(self):
    instance_inferences = self.dataapi_image_instance_inferences()
    metadata = self.dataapi_input_metadata()
    if metadata is None:
      self.register_ping()
      return

    # TODO: what if multiple requests are received?
    # take inferences for every image
    request_id = metadata['payload_context'].get('REQUEST_ID')
    response = {
      'INFERENCES': instance_inferences,
      'REQUEST_ID': request_id,
      'MODEL_ID': self.model_key,
      'MODEL_NAME': self.cfg_objective_name,
      'MODEL_DESCRIPTION': self.cfg_description,
      'TIMESTAMP': self.time(),
    }
    self.register_response(request_id, response)
    return



from core.business.base import CVPluginExecutor
from core.business.base.cv_plugin_executor import _CONFIG as BASE_CONFIG

_CONFIG = {
  **BASE_CONFIG,
  'VALIDATION_RULES': {
    **BASE_CONFIG['VALIDATION_RULES'],
  },

  'AI_ENGINE'                  : 'custom_second_stage_detector',
  'STARTUP_AI_ENGINE_PARAMS'   : {
    'CUSTOM_DOWNLOADABLE_MODEL_URL' : None,
    'MODEL_INSTANCE_ID'             : None,
  },
  'OBJECT_TYPE': ['person'],
  'SECOND_STAGE_DETECTOR_CLASSES' : None,
}

class SecondStageDetectionPlugin(CVPluginExecutor):
  CONFIG = _CONFIG
  def __init__(self, **kwargs):
    super(SecondStageDetectionPlugin, self).__init__(**kwargs)
    return

  def startup(self):
    super().startup()
    assert self.cfg_startup_ai_engine_params.get('CUSTOM_DOWNLOADABLE_MODEL_URL', None) is not None
    assert self.cfg_startup_ai_engine_params.get('MODEL_INSTANCE_ID', None) is not None
    assert self.cfg_second_stage_detector_classes is not None
    # assert len(self.cfg_object_type) == 1
    return

  @property
  def cfg_startup_ai_engine_params(self):
    return self._instance_config.get('STARTUP_AI_ENGINE_PARAMS', {})

  @property
  def cfg_second_stage_detector_classes(self):
    return self._instance_config.get('SECOND_STAGE_DETECTOR_CLASSES', None)

  @property
  def _model_key(self):
    return self._instance_config['STARTUP_AI_ENGINE_PARAMS']['MODEL_INSTANCE_ID']

  def _draw_witness_image(self, img, lst_objects, **kwargs):
    dct_objects_per_class = {
      k: list(filter(lambda x: x[self._model_key][self.ct.TYPE] == k, lst_objects))
      for k in self.cfg_second_stage_detector_classes
    }

    texts = ['{} status:'.format(self._model_key.upper())]
    for k, lst in dct_objects_per_class.items():
      texts.append(' * {} : {} {}s'.format(k, len(lst), self.cfg_object_type[0]))

    text_color = self.ct.DARK_GREEN
    img = self._painter.alpha_text_rectangle_position(
       image=img,
       y_position='top',
       x_position='right',
       y_offset=30,
       text=texts,
       color=text_color
      )

    for idx, res in enumerate(lst_objects):
      top, left, bottom, right = res[self.ct.TLBR_POS]
      prc = res[self._model_key][self.ct.PROB_PRC]
      lbl = res[self._model_key][self.ct.TYPE]
      color = text_color

      img = self._painter.draw_detection_box(
        image=img,
        top=top,
        left=left,
        bottom=bottom,
        right=right,
        label=lbl,
        prc=None,
        color=color
      )
    return img

  def _process(self):
    instance_inferences = self.dataapi_image_instance_inferences()

    if False:
      # todo maybe add some alert logic..
      for idx, res in enumerate(instance_inferences):
        prc = res[self._model_key][self.ct.PROB_PRC]
        lbl = res[self._model_key][self.ct.TYPE]

    payload = None
    if instance_inferences:
      np_witness = self.get_witness_image(
        draw_witness_image_kwargs=dict(lst_objects=instance_inferences),
      )

      payload = self._create_payload(
        img=np_witness,
        lst_objects=instance_inferences,
      )
    #endif
    return payload
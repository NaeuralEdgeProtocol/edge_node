# TODO Bleo: WIP
import torch as th
from plugins.serving.pipelines.base_exe_eng import BaseExeEngTrainingPipeline
from plugins.serving.pipelines.architectures.autoencoder import get_grid_config


class AutoencoderTrainingPipeline(BaseExeEngTrainingPipeline):
  score_key = 'dev_loss'
  score_mode = 'min'

  def model_loss(self, **dct_grid_option):
    return th.nn.BCELoss()

  @property
  def default_grid_search(self):
    return get_grid_config(self.config.get('IMAGE_TYPE', 'BIG'))


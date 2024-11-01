import abc
from naeural_core.local_libraries.nn.th.training.pipelines.base import BaseTrainingPipeline


class BaseExeEngTrainingPipeline(BaseTrainingPipeline, abc.ABC):
  data_factory_loc = 'plugins.serving.pipelines.data'
  model_factory_loc = 'plugins.serving.pipelines.architectures'
  training_callbacks_loc = 'plugins.serving.pipelines.callbacks'


import torch as th
from plugins.serving.pipelines.architectures.marketplace import get_model_factory, get_factory_config


class CustomModelFactory(th.nn.Module):
  def __init__(
      self, model_type='base_classifier', **kwargs
  ):
    super(CustomModelFactory, self).__init__()
    self.model = get_model_factory(model_type)(**kwargs)
    return

  def forward(self, th_x):
    return self.model(th_x)

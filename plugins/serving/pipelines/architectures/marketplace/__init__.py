from plugins.serving.pipelines.architectures.marketplace.advanced_classifier import AdvancedClassifierModelFactory, _CONFIG as ADVANCED_CLASSIFIER_CONFIG
from plugins.serving.pipelines.architectures.marketplace.basic_classifier import BasicClassifierModelFactory, _CONFIG as BASIC_CLASSIFIER_CONFIG


MARKETPLACE_CATALOG = {
  'BASIC_CLASSIFIER': (BasicClassifierModelFactory, BASIC_CLASSIFIER_CONFIG),
  'ADVANCED_CLASSIFIER': (AdvancedClassifierModelFactory, ADVANCED_CLASSIFIER_CONFIG),
}


def get_model_architectures_list():
  return list(MARKETPLACE_CATALOG.keys())


def get_model_factory(model_arch):
  if model_arch.upper() in MARKETPLACE_CATALOG.keys():
    return MARKETPLACE_CATALOG[model_arch.upper()][0]
  raise ValueError(f'Unknown model architecture: {model_arch}')


def get_factory_config(model_arch):
  if model_arch.upper() in MARKETPLACE_CATALOG.keys():
    return MARKETPLACE_CATALOG[model_arch.upper()][1]
  raise ValueError(f'Unknown model architecture: {model_arch}')

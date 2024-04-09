from core import DecentrAIObject

class ServingUtils(DecentrAIObject):
  def __init__(self, **kwargs):
    return

  def get_model_input(self, lst_imgs):
    inputs = [
      {
        "STREAM_NAME": "TEST",
        "STREAM_METADATA": {
          "k1": 0,
          "k2": 1,
        },
        "INPUTS": [
          {
            "TYPE": "IMG",
            "IMG": x,
            "STRUCT_DATA": None,
            "INIT_DATA": None,
            "METADATA": {}
          } for x in lst_imgs
        ]
      }
    ]
    return inputs

if __name__ == '__main__':
  import numpy as np
  from core import Logger
  log = Logger(
    lib_name='EE_TST',
    base_folder='.',
    app_folder='_local_cache',
    config_file='config_startup.txt',
    max_lines=1000,
    TF_KERAS=False
  )
  su = ServingUtils()
  inputs = su.get_model_input([np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)])
  print(inputs)
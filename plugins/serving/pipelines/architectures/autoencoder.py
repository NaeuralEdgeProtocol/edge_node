# TODO Bleo: WIP
from naeural_core.local_libraries.nn.th.training.models.autoencoder import AutoencoderModelFactory, _CONFIG as AUTOENCODER_CONFIG

SMALL_IMAGE_GRID = {
  'in_channels' : [3],
  'prc_noise' : [
    0.3
  ],
  'image_size': [
    [32, 32],
    [128, 192]
  ],
  'layers': [None]
}


BIG_IMAGE_ENCODER = [
  {
   "kernel"  : 3,
   "stride"  : 2,
   "filters" : 32,
   "padding" : 1
  },
  {
   "kernel"  : 3,
   "stride"  : 2,
   "filters" : 64,
   "padding" : 1,
  },
  {
   "kernel"  : 3,
   "stride"  : 2,
   "filters" : 128,
   "padding" : 1,
  },
  {
   "kernel"  : 3,
   "stride"  : 2,
   "filters" : 256,
   "padding" : 1,
  },
  {
   "kernel"  : 3,
   "stride"  : 1,
   "filters" : None, # this will be auto-calculated for last encoding layer
   "padding" : 1,
  },
]


BIG_IMAGE_GRID = {
  'in_channels' : [3],
  'prc_noise' : [
    # 0.3,
    0.5
  ],
  'image_size': [
    [448, 640],
    # [640, 640],
    # [640, 896]
  ],
  'layers': [BIG_IMAGE_ENCODER]
}


def get_grid_config(image_type):
  if isinstance(image_type, str) and image_type.lower() == 'small':
    res_grid = SMALL_IMAGE_GRID
  else:
    res_grid = BIG_IMAGE_GRID

  res_config = {**AUTOENCODER_CONFIG['GRID_SEARCH'], 'GRID': res_grid}
  return res_config


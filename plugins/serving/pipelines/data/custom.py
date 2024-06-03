"""
Documentation: https://docs.google.com/document/d/1B1IP4T1r8aRC4xRehJeDsTfLift_itPQDEFOawrjECE/edit#heading=h.leyw9c7hda59
Streams and other sources that are documented: https://www.dropbox.com/sh/4v6xuag4uprla2n/AACSmOLmxUACdJmCNKwAnx4Wa?dl=0
"""

from typing import Tuple, Union, List, Any

import numpy as np
import os

from core.local_libraries.nn.th.training.data.base import BaseDataLoaderFactory
from core.local_libraries.nn.th.image_dataset_stage_preprocesser import PreprocessResizeWithPad, PreprocessMinMaxNorm
from core.local_libraries.nn.th.training_utils import read_image


class CustomDataLoaderFactory(BaseDataLoaderFactory):
  """
  Data loader factory class.
  The name of the class should be <SIGNATURE>DataLoaderFactory (where <SIGNATURE> is the name of the file)
  """

  def __init__(self, input_size, classes, **kwargs):
    """
    Parameters
    ----------
    classes: list
      List of classes
    """
    self._classes = classes
    self._input_size = input_size
    super(CustomDataLoaderFactory, self).__init__(**kwargs)
    return

  def _lst_on_load_preprocess(self) -> List[Tuple[Any, dict]]:
    return [
      (PreprocessResizeWithPad, dict(h=self._input_size[0], w=self._input_size[1], normalize=False)),
    ]

  def _lst_right_before_forward_preprocess(self) -> List[Tuple[Any, dict]]:
    return []

  def _get_not_loaded_observations_and_labels(self) -> Tuple[Union[List, np.ndarray], Union[List, np.ndarray]]:
    paths = self.dataset_info['paths']
    observations = [p for i, p in enumerate(paths) if not p.endswith('.txt')]
    img_indexes = np.array([i for i, p in enumerate(paths) if not p.endswith('.txt')])

    self.dataset_info['paths'] = observations
    self.dataset_info['path_to_idpath'] = self.dataset_info['path_to_idpath'][img_indexes]

    labels = []
    for img_path in observations:
      base, ext = os.path.splitext(img_path)
      label_path = base + '.txt'
      if os.path.exists(label_path):
        with open(label_path, 'r') as f:
          label = f.read().strip()
        labels.append(label)
      else:
        labels.append(None)

    return observations, labels

  def _load_x_and_y(self, observations, labels, idx) -> Tuple[Union[List, np.ndarray], Union[List, np.ndarray]]:
    x = read_image(observations[idx])
    y_idx = int(labels[idx])
    y = np.zeros(len(self._classes), dtype=np.float32)
    y[y_idx] = 1.0
    return x, y

  def _preprocess(self, x, y, transform):
    x_t = transform(x)
    return x_t, y

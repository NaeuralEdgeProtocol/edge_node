import os
import cv2
import numpy as np

from core import DecentrAIObject
from core import Logger

class Dataset(DecentrAIObject):
  def __init__(self, **kwargs):
    return

  def _load_image(self, path):
    img_bgr = cv2.imread(path)
    img_rgb = img_bgr[:, :, ::-1]
    img = np.ascontiguousarray(img_rgb)
    return img

  def load_images(self, paths):
    assert isinstance(paths, list)
    paths = [
      file for file in paths
      if file.lower().endswith(('.jpg', '.jpeg', 'png', 'bmp'))
    ]
    check_files = [os.path.isfile(x) for x in paths]
    missing = [paths[i] for i, x in enumerate(check_files) if not x]
    if sum(check_files) != len(check_files):
      raise ValueError("Failed to find test images: {}".format(missing))

    imgs = []
    for path in paths:
      img = self._load_image(path)
      # name = os.path.basename(path)
      imgs.append(img)
    #endfor
    return imgs

  def load_images_from_folder(self, path):
    if not os.path.isdir(path):
      raise ValueError('Provided path is not a directory! Please check `{}`'.format(path))

    files = os.listdir(path)
    lst = self.load_images(files)
    return lst


if __name__ == '__main__':
  log = Logger(
    lib_name='EE_TST',
    base_folder='.',
    app_folder='_local_cache',
    config_file='config_startup.txt',
    max_lines=1000,
    TF_KERAS=False
  )
  ds = Dataset()
  ds.test()
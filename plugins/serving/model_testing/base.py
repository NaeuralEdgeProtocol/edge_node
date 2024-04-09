# global dependencies
import random
import torch as th
import pandas as pd
import numpy as np
import cv2
import os
import traceback

from time import sleep
from collections import OrderedDict

# local dependencies
from core import DecentrAIObject
from decentra_vision.draw_utils import DrawUtils
from core.serving.serving_manager import ServingManager
from plugins.serving.model_testing.utils import Dataset
from plugins.serving.model_testing.utils import ServingUtils


class Base(DecentrAIObject):
  def __init__(self,
               model_name,
               test_files,
               sleep_time=10,
               save_plots=True,
               show_plots=False,
               label_extension='json',
               nr_warmup=2,
               nr_predicts=20,
               inprocess=False,
               serving_manager=None,
               print_errors=True,
               subdir_keys=None,
               **kwargs):
    """

    :param model_name: tuple(CLASS, NAME)
      Passed to ServingManager.start_server server_name

    :param test_files: dict(dataset_name: [list of paths])
      Files to run inference on

    :param sleep_time: int
      Sleep time at startup

    :param save_plots: bool
      Whether to save ploted images to disk

    :param show_plots: bool
      Whether to show plotted images

    :param nr_warmup: int
      How many warmup steps to run

    :param nr_predicts: int
      How many predicts to run in order to get mean resource consumption

    :param inprocess: bool
      Whether to run inprocess serving processes

    :param serving_manager: ServingManager object

    :param print_errors: bool
      Whether to display inference errors

    :param subdir_keys: list
      keys used to better organize the saved results (mainly plots) in subdirectories

    :param kwargs:
    """
    super().__init__(**kwargs)
    self._model_name = model_name
    self._test_files = test_files
    self._sleep_time = sleep_time
    self._save_plots = save_plots
    self._show_plots = show_plots
    # self._gpu_device = gpu_device
    self._serving_manager = serving_manager
    # if self._gpu_device is None:
    #   self._gpu_device = 1 if th.cuda.device_count() > 1 else 0
    self._nr_predicts = nr_predicts
    self._nr_warmup = nr_warmup
    self._inprocess = inprocess
    self._print_errors = print_errors
    self.subdir_keys = [] if subdir_keys is None else subdir_keys
    self.current_dct_params = {}

    if self._inprocess is True:
      self.P("WARNING !!! 'inprocess' is set to True which may yield invalid values because of the inability to do a complete cleanup", color='r')
    #
    # self._lst_imgs = None
    # self._lst_img_names = None

    self._dct_res = {
      'MODEL': [],
      'TIME': [],
      'TOTAL_MEM': [],
      'INITIALIZATION_MEM': [],
      'TIME_PER_IMAGE': [],
      'NUMBER_OF_IMAGES': [],
      'SUCCESS': []
    }
    self._test_datasets = {}
    self._test_datasets_paths = {}
    self.label_extension = label_extension
    self._preds = OrderedDict()
    self._init()
    return

  def set_loop_stage(*args, **kwargs):
    return

  def _init(self):
    """Starting serving manager, starting utils. Loading data."""

    if self._serving_manager is None:
      self._serving_manager = ServingManager(
        shmem={},
        log=self.log,
        prefix_log='[TFMGR]',
        owner=self,
      )
    self._painter = DrawUtils(log=self.log)
    self._dataset = Dataset(log=self.log)
    self._serving_utils = ServingUtils(log=self.log)
    self._load_data()
    return

  def _load_data(self):
    """Loading testing dataset from indicated list of files"""

    self.log.P("Preparing data...", color='r')
    self.load_data()
    self.log.P("Done preparing data.")
    return

  def load_data(self):
    for dataset_name, dataset_paths in self._test_files.items():
      self._test_datasets[dataset_name] = self._dataset.load_images(dataset_paths)
      self._test_datasets_paths[dataset_name] = [
        f'{os.path.splitext(dataset_path)[0]}.{self.label_extension}'
        for dataset_path in dataset_paths
      ]
    # self._lst_imgs = list(dct.values())
    # self._lst_img_names = list(dct.keys())
    return

  def run(self, dct_test={}, dct_params={}, _lst_images=None, kill_serving_manager=True):
    """
    TODO: big ambiguity in dct_test vs dct_params

    Execute inference testing

    Video file testing params:
      _lst_images = force the use of the given _lst_images
      kill_serving_manager = set to false in video file testing in order to not create a new manager for every movie batch
    """
    gpu_id = 0
    preds = None

    gpu = dct_test.get('DEFAULT_DEVICE', None)

    if "MAX_BATCH_FIRST_STAGE" not in dct_test:
      self.P("WARNING! Parameter 'MAX_BATCH_FIRST_STAGE' not set. Using default value 5", color='r')

    batch_first_stage = dct_test.get("MAX_BATCH_FIRST_STAGE", 5)
    batch_second_stage = dct_test.get("MAX_BATCH_SECOND_STAGE", 1)

    batch_size = max(batch_first_stage, batch_second_stage)

    run_dct = {
      'DEFAULT_DEVICE': None,
      'MODEL': None,
      'TIME': None,
      'TOTAL_MEM': None,
      'INITIALIZATION_MEM': None,
      'TIME_PER_IMAGE': None,
      'NUMBER_OF_IMAGES': None,
      'SUCCESS': None,
      'PREDICTS': self._nr_predicts,
      'WARMUPS': self._nr_warmup,
      **dct_test
    }
    try:
      # TODO Bleo: Implement cpu testing
      if gpu is not None:
        gpus_info = self.log.gpu_info(show=True, mb=True)[gpu_id]
        gpu_id = [i for i, gpu_info in enumerate(gpus_info) if gpus_info['NAME'] == th.cuda.get_device_name(gpu)][0]

      self.log.P("Running test for {}".format(dct_test), color='g')
      g1 = self.log.gpu_info(show=True, mb=True)[gpu_id]
      self.log.P("Free memory before start: {}".format(g1['FREE_MEM']))

      upstream_config = {
        **dct_test,
        **dct_params
      }
      str_model_name = self._serving_manager.start_server(
        server_name=self._model_name,
        inprocess=self._inprocess,
        upstream_config=upstream_config,
      )
      run_dct['MODEL'] = str_model_name

      g15 = self.log.gpu_info(show=True, mb=True)[gpu_id]
      initialzation_mem = g1['FREE_MEM'] - g15['FREE_MEM']
      run_dct['INITIALIZATION_MEM'] = initialzation_mem

      self.log.P("Model is ready. Check nvidia-smi in next {} seconds...".format(self._sleep_time))
      sleep(self._sleep_time)

      self.log.P("Running warm-up predict...")
      if _lst_images is None:
        _lst_images = self.get_images(dct_test['dataset_name'])

      no_imgs = len(_lst_images)
      _lst_images = (_lst_images * np.ceil(batch_size / no_imgs).astype(int))[:max(batch_size, no_imgs)]
      run_dct['NUMBER_OF_IMAGES'] = len(_lst_images)

      yolo_model_inputs = self._serving_utils.get_model_input(_lst_images)
      for _ in range(self._nr_warmup):
        preds = self._serving_manager.predict(self._model_name, yolo_model_inputs)
      # endfor

      if preds is None and self._nr_warmup > 0:
        raise Exception("Error raised in predict")

      self.log.reset_timers()

      self.log.P("Running batch predict...")
      yolo_model_inputs = self._serving_utils.get_model_input(_lst_images)
      preds = self._serving_manager.predict(self._model_name, yolo_model_inputs)

      if preds is None:
        raise Exception("Error raised in predict")

      for _ in range(self._nr_predicts - 1):
        random.shuffle(_lst_images)
        yolo_model_inputs = self._serving_utils.get_model_input(_lst_images)
        self._serving_manager.predict(self._model_name, yolo_model_inputs)
      # endfor

      self._preds[len(self._preds)] = preds

      g2 = self.log.gpu_info(show=True, mb=True)[gpu_id]
      self.log.P("Free memory after run: {}".format(g2['FREE_MEM']))
      total_model_mem = g1['FREE_MEM'] - g2['FREE_MEM']
      run_dct['TOTAL_MEM'] = total_model_mem
      self.log.P("Model memory {:.0f} MB".format(total_model_mem), color='m')

      self.log.P("Showing results & timers...", color='g')
      self.log.show_timers(title="on {} for '{}' with {}".format(
          self.log.get_machine_name(),
          self._model_name, dct_test
        ),
        div=max(len(_lst_images), 1)
      )

      if dct_test.get('dataset_name') is not None:
        res = self.plot(**{**dct_test, **dct_params})  # TODO: maybe rename .plot in .plot_and_score?
        if res is not None:
          run_dct['SCORE'] = res
        # endif res None
      # endif dataset available

      if not self._show_plots and not self._save_plots:
        self.log.P("Skipped showing images & inferences.")
      # endif

      g3 = self.log.gpu_info(show=True, mb=True)[gpu_id]
      self.log.P("Free memory after shutdown: {}".format(g3['FREE_MEM']))

      if kill_serving_manager:
        self._serving_manager.stop_server(server_name=self._model_name)

      timer_prefix = 'local_pred_' if self._inprocess else 'remote_pred_'
      run_dct['TIME'] = self.log.get_timer(timer_prefix + str_model_name.upper())['MEAN']
      run_dct['TIME_PER_IMAGE'] = self.log.get_timer(timer_prefix + str_model_name.upper())['MEAN'] / len(_lst_images)
      run_dct['SUCCESS'] = True
    except:
      run_dct['SUCCESS'] = False
      if self._print_errors:

        info = traceback.format_exc()
        self.log.P("Inference error: {}".format(info), color='r')
    # endtry

    for k, v in run_dct.items():
      if k not in self._dct_res:
        self._dct_res[k] = []
      self._dct_res[k].append(v)

    th.cuda.empty_cache()
    return preds

  def get_results(self):
    df = pd.DataFrame(self._dct_res)
    return df

  def show_results(self):
    df = self.get_results()
    self.log.set_nice_prints()
    self.log.P("Results on {}:\n{}".format(self.log.get_machine_name(), df))
    return

  @property
  def _testing_subfolder_path(self):
    return self._testing_subfolder_path_helper()

  def _testing_subfolder_path_helper(self, skip_subdirs=False):
    res = os.path.join('testing', self.log.file_prefix, self.__name__, self._model_name)
    if not skip_subdirs and len(self.subdir_keys) > 0:
      values = [self.current_dct_params.get(key) for key in self.subdir_keys if key in self.current_dct_params]
      str_values = [str(value) for value in values]
      res = os.path.join(res, *str_values)
    # endif subdir_keys
    return res

  def save_results(self):
    df = self.get_results()
    df_name = 'results.csv'
    self.log.save_dataframe(df, df_name, folder='output',
                            subfolder_path=self._testing_subfolder_path_helper(skip_subdirs=True))

  def run_tests(self, lst_tests, dct_params, save_results=True):
    # TODO: big ambiguity between lists of test dicts and dct_params
    for dataset_name in self.get_dataset_names():
      for dct_test in lst_tests:
        test_params = {'dataset_name': dataset_name, **dct_test}
        self.current_dct_params = test_params
        self.run(test_params, dct_params)
    # endfor
    self.show_results()
    if save_results:
      self.save_results()
    return self.get_results()

  def plot(self, dataset_name, **kwargs):
    """Draw plots specific to each kind of model"""

    raise NotImplementedError()
    return

  def plot_video(self, cv2_video_writer, lst_imgs, preds, **kwargs):
    """Based on a lst of imgs and preds save a video"""
    raise NotImplementedError()
    return

  def get_images(self, dataset_name):
    return self._test_datasets[dataset_name]

  def get_dataset_names(self):
    return list(self._test_datasets.keys())

  def get_dataset_labels_path(self, dataset_name):
    return self._test_datasets_paths[dataset_name]

  def get_preds(self, idx=None):
    preds = self._preds
    if idx is not None:
      preds = self._preds.get(idx, None)
    return preds

  def get_last_preds(self):
    dct_preds = self.get_preds()
    keys = list(dct_preds.keys())
    preds = dct_preds[keys[-1]]
    return preds

  def get_model_name(self):
    return self._model_name

  def run_video_test(self, video_fn, test_params={}, flip_video=False, movie_batch_size=50, plot_video_kwargs={}):
    """

    :param video_fn:
    :param flip_video:
      False - nothing happens
      Rotate code - passed to cv2.rotate
    :param movie_batch_size:
    :return:
    """
    cap = cv2.VideoCapture(video_fn)
    while not cap.isOpened():
      cap = cv2.VideoCapture(video_fn)

    frames = []
    fps = cap.get(cv2.CAP_PROP_FPS)
    pos_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
    while True:
      flag, frame = cap.read()
      if flip_video is not False:
        frame = cv2.rotate(frame, flip_video)
      frame_rgb = frame[:, :, ::-1]
      frame_rgb = np.ascontiguousarray(frame_rgb)
      frames.append(frame_rgb)

      if cap.get(cv2.CAP_PROP_POS_FRAMES) == cap.get(cv2.CAP_PROP_FRAME_COUNT):
          # If the number of captured frames is equal to the total number of frames,
          # we stop
        break

    output_video_file = '{}_{}'.format(self.log.file_prefix, os.path.split(video_fn)[-1])

    output_video_folder = os.path.join(
      self.log.get_output_folder(),
      'video_testing',
    )
    if not os.path.exists(output_video_folder):
      os.makedirs(output_video_folder)

    output_video_fn = os.path.join(output_video_folder, output_video_file)

    cv2_video_writer = cv2.VideoWriter(
      output_video_fn,
      cv2.VideoWriter_fourcc(*"XVID"),
      fps,
      (frames[0].shape[1], frames[0].shape[0])
    )

    for batch_id in range(len(frames) // movie_batch_size):
      self.P("Processing movie batch {}/{}".format(batch_id + 1, len(frames) // movie_batch_size))
      batch = frames[batch_id * movie_batch_size: (batch_id + 1) * movie_batch_size]
      batch_results = self.run(dct_test={**test_params, "MAX_BATCH_FIRST_STAGE": 5},
                               _lst_images=batch, kill_serving_manager=False)
      self.plot_video(
        cv2_video_writer=cv2_video_writer,
        lst_imgs=batch,
        preds=batch_results,
        **plot_video_kwargs
      )
    cv2_video_writer.release()

    a = 0


if __name__ == '__main__':
  from core import Logger
  from plugins.serving.testing.th_yolov5l6s.data import files as TEST_FILES

  log = Logger('MPTF', base_folder='.', app_folder='_local_cache', TF_KERAS=False)

  # defining script constants
  GPU_DEVICE = 1 if th.cuda.device_count() > 1 else 0
  TESTS = [
    # {
    #   'USE_AMP'         : False,
    #   'USE_FP16'        : False,
    #   'GPU_PREPROCESS'  : False,
    # },

    {
      'USE_AMP': True,
      'USE_FP16': False,
      'GPU_PREPROCESS': True,
      'DEFAULT_DEVICE': 'cuda:' + str(GPU_DEVICE)
    },

    # {
    #   'USE_AMP'         : True,
    #   'USE_FP16'        : False,
    #   'GPU_PREPROCESS'  : True,
    # },

    # {
    #   'USE_AMP'         : False,
    #   'USE_FP16'        : True,
    #   'GPU_PREPROCESS'  : True,
    # },
  ]
  COVERED = 'eff_det0'
  MODEL_NAME = ('th_y5l6s', 'default')

  test = Base(
    log=log,
    model_name=MODEL_NAME,
    test_files=TEST_FILES,
    gpu_device=GPU_DEVICE,
  )

  dct_params = {
    "NEW_PARAM": 0,
    "COVERED_SERVERS": ['th_y5l6', COVERED],
    "NMS_CONF_THR": 0.05,
    "WARMUP_BATCH": len(test.get_images())
  }
  test.run_tests(
    lst_tests=TESTS,
    dct_params=dct_params
  )

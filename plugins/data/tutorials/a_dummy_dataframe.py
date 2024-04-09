

from core.data.base import DataCaptureThread
from core.data.mixins_libs.dataframe_loader_mixin import _DataframeLoaderMixin

_CONFIG = {
  **DataCaptureThread.CONFIG,
  'VALIDATION_RULES' : {
    **DataCaptureThread.CONFIG['VALIDATION_RULES'],
  },
}



class ADummyDataframeDataCapture(DataCaptureThread, _DataframeLoaderMixin):
  """
  Receives a dataframe (json representation or path for read_csv) and sends downstream one line of the dataframe at a time.
  In this way this DCT mimics a VideoFile (which sends data frame by frame).
  """

  CONFIG = _CONFIG

  def __init__(self, **kwargs):
    self._dataframe = None
    self._idx = 0
    super(ADummyDataframeDataCapture, self).__init__(**kwargs)
    return

  def startup(self):
    super().startup()
    self._metadata.update(idx=0, length=None)

  def _init(self):
    self._dataframe = self.dataframe_load()
    self._metadata.length = len(self._dataframe)
    return

  def _release(self):
    return

  def _maybe_reconnect(self):
    if self._idx >= len(self._dataframe):
      self._idx = 0

    return

  def _run_data_aquisition_step(self):

    if self._idx < len(self._dataframe):
      self._metadata.idx = self._idx
      obs = {'OBS': self._dataframe.iloc[self._idx].to_dict()}
      self._add_struct_data_input(obs)
      self._idx += 1
    else:
      self.has_finished_acquisition = True
    #endif

    return


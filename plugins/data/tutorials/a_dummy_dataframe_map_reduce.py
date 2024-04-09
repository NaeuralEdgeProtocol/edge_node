from core.data.base import AbstractMapReduceDataCapture
from core.data.mixins_libs.dataframe_loader_mixin import _DataframeLoaderMixin

_CONFIG = {
  **AbstractMapReduceDataCapture.CONFIG,
  
  'VALIDATION_RULES' : {
    **AbstractMapReduceDataCapture.CONFIG['VALIDATION_RULES'],
  },
}

class ADummyDataframeMapReduceDataCapture(AbstractMapReduceDataCapture, _DataframeLoaderMixin):
  """
  Dummy map-reduce stream:
    - map phase: loads the dataframe provided in "STREAM_CONFIG_METADATA" or in "URL" (see `_DataframeLoaderMixin`),
    splits it in NR_WORKERS chunks. Sends to the map-reduce business plugin this split. The map-reduce business plugin
    knows how to generate de jobs for the workers.
    - reduce phase: waits from the workers the payloads (results of their individual jobs)
    that are just passed to the map-reduce business plugin which knows how to handle that payloads
  """
  CONFIG = _CONFIG
  def __init__(self, **kwargs):
    self._chunks = None
    super(ADummyDataframeMapReduceDataCapture, self).__init__(**kwargs)
    return

  def startup(self):
    super().startup()
    self._metadata.update(input_indexes=None)
    return

  @property
  def _file_url(self):
    return self.cfg_url

  def _init_map(self):
    df = self.dataframe_load()

    chunk_size = len(df) // self.nr_chunks
    if len(df) % self.nr_chunks > 0:
      chunk_size += 1

    self._chunks, indexes = [], []
    for i in range(self.nr_chunks):
      start_chunk = i * chunk_size
      end_chunk = (i+1)*chunk_size
      indexes.append([start_chunk, end_chunk])
      self._chunks = [df.iloc[start_chunk : end_chunk].to_json() for i in range(self.nr_chunks)]
    #endfor
    self._metadata.input_indexes = indexes
    return

  def _release_map(self):
    return

  def _maybe_reconnect_map(self):
    return

  def _run_data_aquisition_step_map(self):
    obs = dict(chunks=self._chunks)
    self._add_struct_data_input(obs)


    # if finished all chunks, self._finished_map = True!

    # mandatory set this to True.
    # please also check `video_file_map_reduce` to see that in `_run_data_aquisition_step_map`, progress is sent
    # until the upload is finished and just when the upload is finished the final struct data is sent and the map phase
    # is really finished!
    self._finished_map = True
    return

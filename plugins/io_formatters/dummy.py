# local dependencies
from PyE2.io_formatter import BaseFormatter


class DummyFormatter(BaseFormatter):

  def __init__(self, log, **kwargs):
    super(DummyFormatter, self).__init__(
        log=log, prefix_log='[DEFAULT-FMT]', **kwargs)
    return

  def startup(self):
    pass

  def _encode_output(self, output):
    output['DUMMY_ENTRY'] = "Dummy_entry"
    return output

  def _decode_output(self, encoded_output):
    encoded_output.pop('DUMMY_ENTRY', None)
    return encoded_output

  def _decode_streams(self, dct_config_streams):
    return dct_config_streams

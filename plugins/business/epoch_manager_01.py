from core.business.base.web_app import FastApiWebAppPlugin
__VER__ = '0.1.0.0'

_CONFIG = {
  **FastApiWebAppPlugin.CONFIG,
  'USE_NGROK' : False,
  'NGROK_ENABLED' : False,
  'NGROK_DOMAIN' : None,
  'NGROK_EDGE_LABEL' : None,

  'PORT' : None,
  'ASSETS' : 'plugins/business/fastapi/epoch_manager',
  'VALIDATION_RULES': {
    **FastApiWebAppPlugin.CONFIG['VALIDATION_RULES'],
  },
}

class EpochManager01Plugin(FastApiWebAppPlugin):
  CONFIG = _CONFIG

  def __init__(self, **kwargs):
    super(EpochManager01Plugin, self).__init__(**kwargs)
    return

  def __get_response(self, dct_data: dict):
    str_utc_date = self.datetime.now(self.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    dct_data['server_id'] = self.node_addr
    dct_data['server_time'] = str_utc_date
    dct_data['server_current_epoch'] = self.__get_current_epoch()
    dct_data['server_uptime'] = str(self.timedelta(seconds=int(self.time_alive))) # TODO: make in the format "84 days, 8:47:51"
    return dct_data

  def __get_current_epoch(self):
    return self.netmon.epoch_manager.get_current_epoch()

  # List of endpoints, these are basically wrappers around the netmon
  # epoch manager.

  @FastApiWebAppPlugin.endpoint
  # /nodes_list
  def nodes_list(self):
    nodes = self.netmon.epoch_manager.get_node_list()
    response = self.__get_response({
      'nodes': nodes,
    })
    return response

  @FastApiWebAppPlugin.endpoint
  # /node_epochs
  def node_epochs(self, node_addr):
    if node_addr is None:
      return None
    if not isinstance(node_addr, str):
      return None
    epochs_vals = self.netmon.epoch_manager.get_node_epochs(node_addr)

    response = self.__get_response({
      'node': node_addr,
      'epochs_vals': epochs_vals,
    })
    return response

  @FastApiWebAppPlugin.endpoint
  # /node_epoch
  def node_epoch(self, node_addr, epoch):
    if node_addr is None or epoch is None:
      return None
    if not isinstance(node_addr, str):
      return None
    if isinstance(epoch, str):
      epoch = int(epoch)
    if not isinstance(epoch, int):
      return None
    epoch_val = self.netmon.epoch_manager.get_node_epoch(node_addr, epoch)

    response = self.__get_response({
      'node': node_addr,
      'epoch_id': epoch,
      'epoch_val': epoch_val,
      'epoch_prc': round(epoch_val / 255, 4),
    })
    return response

  @FastApiWebAppPlugin.endpoint
  # /node_last_epoch
  def node_last_epoch(self, node_addr):
    if node_addr is None:
      return None
    if not isinstance(node_addr, str):
      return None
    last_epoch_val = self.netmon.epoch_manager.get_node_last_epoch(node_addr)

    response = self.__get_response({
      'node': node_addr,
      'last_epoch_id': self.__get_current_epoch() - 1,
      'last_epoch_val': last_epoch_val,
      'last_epoch_prc': round(last_epoch_val / 255, 4),
    })
    return response

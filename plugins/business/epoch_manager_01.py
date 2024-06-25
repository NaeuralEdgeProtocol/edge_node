from core.business.base.web_app import FastApiWebAppPlugin
__VER__ = '0.1.0.0'

_CONFIG = {
  **FastApiWebAppPlugin.CONFIG,
  'ASSETS' : 'epoch_manager',
  'VALIDATION_RULES': {
    **FastApiWebAppPlugin.CONFIG['VALIDATION_RULES'],
  },
}

class EpochManager01Plugin(FastApiWebAppPlugin):
  CONFIG = _CONFIG

  def __init__(self, **kwargs):
    super(EpochManager01Plugin, self).__init__(**kwargs)
    return

  # List of endpoints, these are basically wrappers around the netmon
  # epoch manager.

  @FastApiWebAppPlugin.endpoint
  def get_current_epoch(self):
    return self.netmon.epoch_manager.get_current_epoch()

  @FastApiWebAppPlugin.endpoint
  def get_nodes_list(self):
    return self.netmon.epoch_manager.get_node_list()

  @FastApiWebAppPlugin.endpoint
  def get_node_epochs(self, node_addr):
    if node_addr is None:
      return None
    if not isinstance(node_addr, str):
      return None
    return self.netmon.epoch_manager.get_node_epochs(node_addr)

  @FastApiWebAppPlugin.endpoint
  def get_node_epoch(self, node_addr, epoch):
    if node_addr is None or epoch is None:
      return None
    if not isinstance(node_addr, str):
      return None
    if isinstance(epoch, str):
      epoch = int(epoch)
    if not isinstance(epoch, int):
      return None
    ret = self.netmon.epoch_manager.get_node_epoch(node_addr, epoch)
    return ret

  @FastApiWebAppPlugin.endpoint
  def get_node_last_epoch(self, node_addr):
    if node_addr is None:
      return None
    if not isinstance(node_addr, str):
      return None
    return self.netmon.epoch_manager.get_node_last_epoch(node_addr)

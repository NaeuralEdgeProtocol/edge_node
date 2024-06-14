from core.business.base.fastapi import BaseFastapiPlugin as Base
from core.business.base.fastapi import _CONFIG as BASE_CONFIG

__VER__ = '0.1.0.0'

_CONFIG = {
  **BASE_CONFIG,
  'ASSETS' : 'epoch_manager',
  'VALIDATION_RULES': {
    **BASE_CONFIG['VALIDATION_RULES'],
  },
}

class EpochManager01Plugin(Base):
  CONFIG = _CONFIG

  def __init__(self, **kwargs):
    super(EpochManager01Plugin, self).__init__(**kwargs)
    return

  # List of endpoints, these are basically wrappers around the netmon
  # epoch manager.

  @Base.endpoint
  def get_current_epoch(self):
    return self.netmon.epoch_manager.get_current_epoch()

  @Base.endpoint
  def get_nodes_list(self):
    return self.netmon.epoch_manager.get_node_list()

  @Base.endpoint
  def get_node_epochs(self, node_addr):
    if node_addr is None:
      return None
    if not isinstance(node_addr, str):
      return None
    return self.netmon.epoch_manager.get_node_epochs(node_addr)

  @Base.endpoint
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

  @Base.endpoint
  def get_node_last_epoch(self, node_addr):
    if node_addr is None:
      return None
    if not isinstance(node_addr, str):
      return None
    return self.netmon.epoch_manager.get_node_last_epoch(node_addr)

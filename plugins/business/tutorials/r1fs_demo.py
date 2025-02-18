"""
{
    "CAP_RESOLUTION": 1,
    "LIVE_FEED": true,
    "NAME": "R1FS_DEMO",
    "PLUGINS": [

        {
            "INSTANCES": [
                {
                    "INSTANCE_ID": "DEFAULT"
                }
            ],
            "SIGNATURE": "R1FS_DEMO"
        }
        
    ],
    "TYPE": "Void"
}  
  
"""


from naeural_core.business.base import BasePluginExecutor as BasePlugin



__VER__ = '0.1.0.0'

_CONFIG = {

  # mandatory area
  **BasePlugin.CONFIG,

  # our overwritten props
  'PROCESS_DELAY' : 30,

  'LOG_MESSAGE'   : '',

  'VALIDATION_RULES' : {
    **BasePlugin.CONFIG['VALIDATION_RULES'],    
  },  

}

class R1fsDemoPlugin(BasePlugin):
  
  def __save_some_data(self):
    self.P("Saving some data...")
    uuid1 = self.uuid()
    uuid2 = self.uuid()
    data = {
      'key1': uuid1,
      'key2': uuid2,
      'owner' : self.str_unique_identification
    }
    # TODO: r1fs.add_json or yaml
    cid = None
    return cid
  
  def __announce_cid(self, cid):
    self.P(f'Announcing CID: {cid}')
    # TODO: use CSTORE hash "r1fs.announce_cid" to announce the CID
    return    
  
  def __get_announced_cids(self):
    cids = []
    self.P("Checking for any announced CIDs...")
    # TODO: use CSTORE hash "r1fs.announce_cid" to get any external CIDs
    return cids
  
  def share_data(self):
    self.P("Sharing data...")
    cid = self.__save_some_data()
    self.__announce_cid(cid)
    return cid
  
  def show_others_shared_data(self):
    cids = self.__get_announced_cids()
    self.P(f"Found {len(cids)} shared data...")
    for cid in cids:
      self.P(f"Shared data: {cid}")
      # TODO: use r1fs.get_file to get the shared data and 
      # TODO: dump the incoming json
    return
    


  def process(self):
    self.log('R1fsDemoPlugin is processing...')
    self.share_data()
    self.show_others_shared_data()
    self.log('R1fsDemoPlugin is done.')
    return
"""
{
    "NAME": "R1FS_DEMO_PIPELINE",
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
  'PROCESS_DELAY' : 15,
  
  'INITIAL_WAIT'  : 15,

  'LOG_MESSAGE'   : '',

  'VALIDATION_RULES' : {
    **BasePlugin.CONFIG['VALIDATION_RULES'],    
  },  

}

class R1fsDemoPlugin(BasePlugin):
  
  def on_init(self):
    # we store a unique ID for this instance 
    self.my_id = f'{self.ee_id}_{self.uuid(size=2)}'
    self.__file_send_time = 0
    self.__known_cids = []
    self.__start_time = self.time()
    self.P(f'R1fsDemoPlugin v{__VER__} with ID: {self.my_id}')
    self.P(f"Plugin instance will now wait for {self.cfg_initial_wait} sec")
    return
  
  def __save_some_data(self):
    """
    The purpose of this method is to save some data to the R1FS and return the CID
    of the saved data. The data is a simple dictionary with some arbitrary values 
    just for demonstration purposes.
    
    """
    self.P("Saving some data...")
    uuid = self.uuid() # generate some random data
    value = self.np.random.randint(1, 100) # even more random data
    data = {
      'some_key': uuid,
      'other_key': value,
      'some_owner_key' : self.full_id
    }
    cid = self.r1fs.add_yaml(data)
    self.P(f"Data saved with CID: {cid}")
    return cid
  
  def __announce_cid(self, cid):
    self.P(f'Announcing CID: {cid}')
    self.chainstore_hset(hkey='r1fs-demo', key=self.my_id, value=cid)
    return    
  
  def __get_announced_cids(self):
    cids = []
    self.P("Checking for any announced CIDs...")
    # get full dictionary of all announced CIDs under the key 'r1fs-demo'
    # we assume all demo instances are using the same hkey and their own key
    dct_data = self.chainstore_hgetall('r1fs-demo')
    if dct_data:
      # extract all the CIDs except our own
      cids = [
        v for k, v in dct_data.items() if k != self.my_id
      ]
      # now we filter based on already known CIDs
      cids = [
        cid for cid in cids if cid not in self.__known_cids
      ]
    if len(cids) > 0:
      self.P(f"Found {len(cids)} CIDs ")
      self.__known_cids.extend(cids)
    return cids
  
  def share_local_data(self):
    if self.time() - self.__file_send_time > 3600:
      self.P("Sharing data...")
      cid = self.__save_some_data()
      self.__announce_cid(cid)
    return cid
  
  def show_remote_shared_data(self):
    cids = self.__get_announced_cids()
    self.P(f"Found {len(cids)} shared data...")
    for cid in cids:
      self.P(f"Retrieving: {cid}")
      fn = self.r1fs.get_file(cid)
      self.P(f"Retrieved: {fn}")
      if fn.endswith('.yaml') or fn.endswith('.yml'):
        self.P(f"Processing YAML file: {fn}")
        with open(fn, 'r') as fh:
          data = self.yaml.load(fh)
        self.P(f"Loaded:\n {self.json_dumps(data, indent=2)}")
      else:
        self.P(f"Received unsupported file: {fn}", color='r')
    # end for each CID
    return
    


  def process(self):
    if self.time() - self.__start_time < self.cfg_initial_wait:
      self.P(f"Waiting for {self.cfg_initial_wait} sec to start processing...")
      return
    self.log('R1fsDemoPlugin is processing...')
    self.share_local_data()
    self.show_remote_shared_data()
    self.log('R1fsDemoPlugin is done.')
    return
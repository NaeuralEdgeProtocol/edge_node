from naeural_core.constants import ADMIN_PIPELINE
import os


ADMIN_PIPELINE = {
  **ADMIN_PIPELINE,
  'EPOCH_MANAGER_01': {
    "NGROK_EDGE_LABEL": os.environ.get("EE_NGROK_EDGE_LABEL_EPOCH_MANAGER"),
    "PROCESS_DELAY": 0,
  },

  "NAEURAL_RELEASE_APP": {
    "NGROK_EDGE_LABEL": os.environ.get("EE_NGROK_EDGE_LABEL_RELEASE_APP"),
  }
  
}


if __name__ == '__main__':
  print("")

from naeural_core.constants import ADMIN_PIPELINE, ADMIN_PIPELINE_FILTER


ADMIN_PIPELINE_FILTER = [
  *ADMIN_PIPELINE_FILTER,
  "ORACLE_SYNC_01",
]

#############    Era information    ###############
DEFAULT_GENESYS_EPOCH_DATE = "2025-01-28 20:00:00"      # "2025-02-03 17:00:00" for mainnet
DEFAULT_EPOCH_INTERVALS =  1                            # 24 mainnet, 1 for devnet
DEFAULT_EPOCH_INTERVAL_SECONDS = 3600                   # 3600
SUPERVISOR_MIN_AVAIL_PRC = 0.50                         # 0.98 for mainnet, 60% for testnet
###################################################


ADMIN_PIPELINE = {
  **ADMIN_PIPELINE,
  'ORACLE_SYNC_01': {
  },

  'EPOCH_MANAGER_01': {
    "NGROK_EDGE_LABEL": "$EE_NGROK_EDGE_LABEL_EPOCH_MANAGER",
    "PROCESS_DELAY": 0,
  },

  "NAEURAL_RELEASE_APP": {
    "NGROK_EDGE_LABEL": "$EE_NGROK_EDGE_LABEL_RELEASE_APP",
    "PROCESS_DELAY": 0,
  },
  
  'DAUTH_MANAGER': {
    "NGROK_EDGE_LABEL": "$EE_NGROK_EDGE_LABEL_DAUTH_MANAGER",
    "PROCESS_DELAY": 0,
    
    "AUTH_ENV_KEYS" : [
      "EE_MQTT_HOST",
      "EE_MQTT_PORT",
      "EE_MQTT_USER",
      "EE_MQTT",
      "EE_MQTT_SUBTOPIC",
      "EE_MQTT_CERT",
      
      "EE_GITVER",
      
      "EE_MINIO_ENDPOINT",
      "EE_MINIO_ACCESS_KEY",
      "EE_MINIO_SECRET_KEY",
      "EE_MINIO_SECURE",
      
      "EE_MINIO_MODEL_BUCKET",
      "EE_MINIO_UPLOAD_BUCKET",
      
      "EE_NGROK_AUTH_TOKEN",
    ],
    
    "AUTH_PREDEFINED_KEYS" : {
      # "EE_SUPERVISOR" : False, # this should not be enabled 
      "EE_SECURED" : 1
    },
  },
  
  'CSTORE_MANAGER': {
    "NGROK_EDGE_LABEL": "$EE_NGROK_EDGE_LABEL_CSTORE_MANAGER",
    "PROCESS_DELAY": 0,
  },
  
}


if __name__ == '__main__':
  print("")

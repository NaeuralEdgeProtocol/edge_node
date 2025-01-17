from naeural_core.constants import ADMIN_PIPELINE
import os


ADMIN_PIPELINE = {
  **ADMIN_PIPELINE,
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
    ],
    
    "AUTH_PREDEFINED_KEYS" : {
      "EE_SUPERVISOR" : False,
      "EE_SECURED" : 1
    },
  },
  
}


if __name__ == '__main__':
  print("")

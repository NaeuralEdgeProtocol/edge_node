"""
{
    "CAP_RESOLUTION": 1,
    "LIVE_FEED": true,
    "NAME": "TS_REST_AND_OTHER",
    "PLUGINS": [

        {
            "INSTANCES": [
                {
                    "INSTANCE_ID": "DEFAULT"
                }
            ],
            "SIGNATURE": "A_DUMMY_TAGGING_MASTER"
        }

    ],
    "RECONNECTABLE": true,
    "STREAM_CONFIG_METADATA": {

    },
    "TYPE": "IotQueueListener"
}


This plugin is the master part in the Tagger application
"""


from naeural_core.business.base import BasePluginExecutor as BasePlugin


__VER__ = "0.1.0.0"

_CONFIG = {

  # mandatory area
  **BasePlugin.CONFIG,

  # our overwritten props
  "P2P_MESSAGE_TYPE": None,
  "JOB_DETAILS": None,

  "JOB_PROGRESS": 0,

  "PROCESS_DELAY": 0.1,
  "ALLOW_EMPTY_INPUTS" : True,

  "VALIDATION_RULES": {
    **BasePlugin.CONFIG["VALIDATION_RULES"],
  },

}


class ADummyTaggingMasterPlugin(BasePlugin):
  CONFIG = _CONFIG

  def __init__(self, **kwargs):
    super(ADummyTaggingMasterPlugin, self).__init__(**kwargs)
    self.__state = "created"
    self.__state_methods = {
      "created": self._created_state,
      "waiting_workers": self._waiting_workers_state,
      "waiting_progress": self._waiting_progress_state,

      "exiting": self._exiting_state,
      "killed": self._killed_state,
    }

    self.__worker_eeid = None
    self.__worker_pipeline_name = None
    self.__worker_instance_id = None
    self.__worker_signature = None

    self._result = None
    self._payload_kwargs = {}
    return

  def _created_state(self):
    """
    In this state we were just created by the interface. We have to send the `Master`, aka `Sender`
    information that we want to do this job.
    """

    payload = self._create_payload(**{
      "BCAST_MESSAGE_TYPE": "BCAST NEED",
      "JOB_TYPE": "A_DUMMY_TAGGING_WORKER",
      "JOB_ID": self.get_instance_id(),
    })

    self.__state = 'waiting_workers'

    return payload

  def _waiting_workers_state(self):
    dct_message = self.dataapi_struct_data()
    if dct_message is None:
      return
    message_type = dct_message.get('BCAST_MESSAGE_TYPE')
    worker_eeid = dct_message.get("EE_ID")
    worker_pipeline_name = dct_message.get("PIPELINE")
    worker_instance_id = dct_message.get("INSTANCE_ID")
    worker_signature = dct_message.get("SIGNATURE")
    self.P(message_type)
    if message_type != "I WANT":
      return

    if worker_instance_id != self.get_instance_id():
      return

    self.__worker_pipeline_name = worker_pipeline_name
    self.__worker_eeid = worker_eeid
    self.__worker_instance_id = worker_instance_id
    self.__worker_signature = worker_signature

    payload = self._create_payload(**{
      "BCAST_MESSAGE_TYPE": "ACCEPTED",

      "WORKER_EEID": self.__worker_eeid,
      "WORKER_PIPELINE_NAME": self.__worker_pipeline_name,
      "WORKER_INSTACE_ID": self.__worker_instance_id,
      "WORKER_SIGNATURE": self.__worker_signature,
    })

    self.cmdapi_register_command(self.__worker_eeid, "UPDATE_PIPELINE_INSTANCE", {
      self.consts.PAYLOAD_DATA.NAME: self.__worker_pipeline_name,
      self.consts.PAYLOAD_DATA.SIGNATURE: self.__worker_signature,
      self.consts.PAYLOAD_DATA.INSTANCE_ID: self.__worker_instance_id,
      self.consts.PAYLOAD_DATA.INSTANCE_CONFIG: {
        "P2P_MESSAGE_TYPE": "ACCEPTED",

        "JOB_DETAILS": "IT`S A ME"
      },
    })

    self.__state = 'waiting_progress'

    return payload

  def _waiting_progress_state(self):
    #todo: handle progress not coming for some time
    if self.cfg_p2p_message_type not in ["PROGRESS","DONE"]:
      return

    payload = None
    if self.cfg_p2p_message_type == "PROGRESS":
      self.P("Received Progress: {}".format(self.cfg_job_progress))
    else:
      payload = self._create_payload(**{
        "BCAST_MESSAGE_TYPE": "BCAST DONE",

        "JOB_ID": self.get_instance_id(),

        "WORKER_EEID": self.__worker_eeid,
        "WORKER_PIPELINE_NAME": self.__worker_pipeline_name,
        "WORKER_INSTACE_ID": self.__worker_instance_id,
        "WORKER_SIGNATURE": self.__worker_signature,
      })

      self.__state = 'exiting'

    self.update_config_data({
      "P2P_MESSAGE_TYPE": None,
    })

    return payload


  def _exiting_state(self):
    self.cmdapi_stop_current_pipeline()
    self.__state = 'killed'
    return

  def _killed_state(self):
    return


  def _process(self):
    # self.P(self.__state)

    return self.__state_methods[self.__state]()

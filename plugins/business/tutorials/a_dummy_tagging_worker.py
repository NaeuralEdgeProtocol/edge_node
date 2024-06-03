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
            "SIGNATURE": "A_DUMMY_TAGGING_WORKER"
        }

    ],
    "RECONNECTABLE": true,
    "STREAM_CONFIG_METADATA": {

    },
    "TYPE": "IotQueueListener"
}


This plugin is the worker part in the Tagger application
"""


from core.business.base import BasePluginExecutor as BasePlugin


__VER__ = "0.1.0.0"

_CONFIG = {

  # mandatory area
  **BasePlugin.CONFIG,

  # our overwritten props
  "PROGRESS_INTERVAL": 60,
  "SENDER_EEID": "eeid",
  "SENDER_PIPELINE": "pipeline",
  "SENDER_PLUGIN": "plugin",
  "SENDER_INSTANCE": "instance",

  "P2P_MESSAGE_TYPE": None,
  "JOB_DETAILS": None,

  "PROCESS_DELAY": 0.1,
  "JOB_PROGRESS": 0,
  "ALLOW_EMPTY_INPUTS" : True,

  "VALIDATION_RULES": {
    **BasePlugin.CONFIG["VALIDATION_RULES"],
  },

}


class ADummyTaggingWorkerPlugin(BasePlugin):
  CONFIG = _CONFIG

  def __init__(self, **kwargs):
    super(ADummyTaggingWorkerPlugin, self).__init__(**kwargs)
    self.__state = "created"
    self.__state_methods = {
      "created": self._created_state,
      "waiting": self._waiting_state,
      "accepted": self._accepted_state,
      "progress": self._progress_state,
      "done": self._done_state,

      "exiting": self._exiting_state,
      "killed": self._killed_state,
    }

    self._progress = 0
    self._result = None
    self._payload_kwargs = {}
    return

  def _created_state(self):
    """
    In this state we were just created by the interface. We have to broadcast the
    information that we want to do this job.
    """

    # broadcast "I want" job message
    self._payload_kwargs = {
      "BCAST_MESSAGE_TYPE": "I WANT",
    }

    payload = self._create_payload(**self._payload_kwargs)
    self.__state = "waiting"

    return payload

  def _waiting_state(self):
    """
    In this state we are waiting for a response from the `Sender`. The response can either be a p2p
    message with the job or a broadcast with the message that it chose another worker.
    """

    if self.cfg_p2p_message_type is not None:
      if self.cfg_p2p_message_type == "ACCEPTED":
        self.__state = "accepted"
      else:
        # maybe change this
        self.__state = "exiting"
    else:
      dct_message = self.dataapi_struct_data()
      if dct_message is None:
        return

      is_expected_sender = dct_message.get("EEID") == self.cfg_sender_eeid
      is_expected_bcast = dct_message.get("BCAST_MESSAGE_TYPE") == "BCAST ACCEPTED"
      is_expected_job = dct_message.get("JOB_ID") == self.get_instance_id()
      is_expected_worker = dct_message.get("WORKER") == self._device_id

      if is_expected_sender and is_expected_bcast and is_expected_job and not is_expected_worker:
        self.__state = "exiting"

    return

  def _accepted_state(self):
    """
    In this state we have been selected to do the job. We need to be prepared
    """
    self.__state = "progress"
    return

  def _progress_state(self):
    """
    In this state we are doing the job. We are sending payloads with progress status periodically.

    Returns
    -------
    Payload, None | opt
        The payload with the progress so far
    """
    if self._progress == self.cfg_job_progress:
      return

    self.P(self.cfg_job_progress)
    if self.cfg_job_progress == 100:
      self._result = self.cfg_job_details
      self.__state = "done"

    self.cmdapi_register_command(self.cfg_sender_eeid, "UPDATE_PIPELINE_INSTANCE", {
      self.consts.PAYLOAD_DATA.NAME: self.cfg_sender_pipeline,
      self.consts.PAYLOAD_DATA.SIGNATURE: self.cfg_sender_plugin,
      self.consts.PAYLOAD_DATA.INSTANCE_ID: self.cfg_sender_instance,
      self.consts.PAYLOAD_DATA.INSTANCE_CONFIG: {
        "P2P_MESSAGE_TYPE": "PROGRESS" if self.cfg_job_progress < 100 else "DONE",
        "JOB_ID": self.get_instance_id(),
        "JOB_RESULTS": None if self.cfg_job_progress < 100 else self._result,
        "JOB_PROGRESS": self.cfg_job_progress if self.cfg_job_progress < 100 else None,
      },
    })

    self._progress = self.cfg_job_progress

    return
    # return payload

  def _done_state(self):
    """
    In this state we sent the final payload and we are waiting for a confirmation. If it does not arrive,
    we should resend the payload.
    """

    dct_message = self.dataapi_struct_data()
    if dct_message is None:
      return
    is_expected_sender = dct_message.get("EE_ID") == self.cfg_sender_eeid
    is_expected_bcast = dct_message.get("BCAST_MESSAGE_TYPE") == "BCAST DONE"
    is_expected_job = dct_message.get("JOB_ID") == self.get_instance_id()
    is_expected_worker = dct_message.get("WORKER_EEID") == self._device_id

    if is_expected_sender and is_expected_bcast and is_expected_job and is_expected_worker:
      self.__state = "exiting"

    return

  def _exiting_state(self):
    """
    In this state we are shutting us down, since there is nothing left to do.
    """
    # for now this is good, but we need to delete only this instance
    self.cmdapi_stop_current_pipeline()
    self.__state = "killed"
    return

  def _killed_state(self):
    return

  def _process(self):
    # self.P(self.__state)

    return self.__state_methods[self.__state]()

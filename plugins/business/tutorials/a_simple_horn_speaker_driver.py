"""
In this tutorial we are going to demonstrate how to create a simple driver for a horn speaker.
We are going to use the ExternalProgramDevice as a base class for the driver.
The ExternalProgramDevice is a base class for drivers that run external programs according to a schema.
The schema is defined in the configuration, and it is used to validate the arguments that are passed to the external program.

This is an example pipeline that uses the horn speaker driver:
{
    "INSTANCES": [
        {
            "FORCED_PAUSE": false,
            "INSTANCE_ID": "INSTANCE_1",
        }
    ],
    "SIGNATURE": "A_SIMPLE_HORN_SPEAKER_DRIVER"
}

This is an example instance command that the horn speaker driver can receive:
"INSTANCE_COMMAND": {
    "action": "PLAY_MP3_SOUND",
    "bucket_name": "horn-sounds",
    "hornaddress": "rtp://127.0.0.1:9000",
    "soundfile": "minio:sound.mp3"
}

In the above example, the driver will play the sound file "sound.mp3" from the "horn-sounds" bucket
on the horn speaker at "rtp://127.0.0.1:9000".

By passing the "action" parameter, we can specify what method will be called by the plugin
upon receiving and instance command.

Note that in order for your method to be called, it must be prefixed with "device_action_" and the
value of the "action" parameter must be in uppercase and follow the snakecase convention.
"""
from core.business.base.drivers import ExternalProgramDevice

__VER__ = '1.0.0'

_CONFIG = {
  **ExternalProgramDevice.CONFIG,

  'ALLOW_EMPTY_INPUTS': True,

  "PROCESS_DELAY": 10,

  "COOLDOWN": 3,

  'VALIDATION_RULES': {
    **ExternalProgramDevice.CONFIG['VALIDATION_RULES'],
  },

  "EXTERNAL_PROGRAM_SCHEMA": {
    "program": "ffmpeg",
    "allow_reentrant": False,
    "arguments": [
      {"value": "-re", "type": "static"},
      {"value": "-f", "type": "static"},
      {"value": "", "type": "dynamic", "name": "extension"},
      {"value": "-i", "type": "static"},
      {"value": "", "type": "file", "name": "soundfile", "force": True},
      {"value": "-acodec", "type": "static"},
      {"value": "", "type": "dynamic", "name": "codec"},
      {"value": "-f", "type": "static"},
      {"value": "rtp", "type": "static"},
      {"value": "", "type": "dynamic", "name": "hornaddress"}
    ]
  },

  "DEBUG": True,
}


class ASimpleHornSpeakerDriverPlugin(ExternalProgramDevice):
  CONFIG = _CONFIG

  def __init__(self, **kwargs):
    super(ASimpleHornSpeakerDriverPlugin, self).__init__(**kwargs)
    return

  def __parse_file_extension_and_codec(self, file):
    """
    Obtain file extension and codec
    Parameters
    ----------
    file

    Returns
    -------
    str
    """
    # Extract the extension from the file name
    ext = file.rsplit('.', 1)[-1].lower()  # This will get 'mp3' from 'minio:sound.mp3'

    # Determine the codec based on the extension
    codec = 'mp2' if ext == 'mp3' else 'aac'
    return ext, codec

  def _process_dynamic_params(self, files: dict, **kwargs):
    """
    Process dynamic parameters for the external program (ffmpeg)
    Parameters
    ----------
    files
    kwargs

    Returns
    -------
    list
    """
    # Assume extension and codec are determined from the soundfile
    extension, codec = self.__parse_file_extension_and_codec(files.get("soundfile"))

    updated_args = []
    for arg in self.device_get_current_schema()["arguments"]:
      if arg["type"] == "dynamic":
        if arg["name"] == "extension":
          arg["value"] = extension
        elif arg["name"] == "codec":
          arg["value"] = codec
        elif arg["name"] == "hornaddress":
          arg["value"] = kwargs.get("hornaddress")
      if arg["type"] == "file":
        arg["value"] = files.get(arg["name"])
      updated_args.append(arg["value"])

    if self.cfg_debug:
      self.P(f"Updated args: {updated_args}, files: {files}", color='yellow')
    return updated_args

  def device_action_play_mp3_sound(self, soundfile, hornaddress, **args):
    """
    Play a sound file on the horn speaker, using ffmpeg to stream the sound to the horn address
    We are trying to launch the following command: ffmpeg -re -f mp3 -i sound.mp3 -acodec mp2 -f rtp rtp://ip:port
    And we are assuming that the sound file is a mp3 file
    Parameters
    ----------
    soundfile : str
    hornaddress : str
    args : dict

    Returns
    -------

    """
    try:
      self.device_run_external_program(hornaddress=hornaddress, soundfile=soundfile, **args)
    except Exception as e:
      if self.cfg_debug:
        self.P(f"Error playing sound: {e}", color='red')
      self.add_payload_by_fields(error=f"Error playing sound: {e}", )

  def device_action_play_wav_sound(self, soundfile, hornaddress, **args):
    """
    Play a sound file on the horn speaker, using ffmpeg to stream the sound to the horn address
    We are trying to launch the following command: ffmpeg -re -f wav -i sound.wav -acodec aac -f rtp rtp://ip:port
    And we are assuming that the sound file is a wav file
    Parameters
    ----------
    soundfile : str
    hornaddress : str
    args : dict

    Returns
    -------

    """
    try:
      self.device_run_external_program(hornaddress=hornaddress, soundfile=soundfile, **args)
    except Exception as e:
      if self.cfg_debug:
        self.P(f"Error playing sound: {e}", color='r')
      self.add_payload_by_fields(error=f"Error playing sound: {e}", )

from PyE2 import Session


def job_data_to_id(node_id, pipeline, signature, instance):
  return instance


def classes_dict_to_msg(classes):
  return [{'name': k, 'description': v} for k, v in classes.items()]


def classes_msg_to_dict(classes):
  return {c['name']: c['description'] for c in classes}


def process_data_sources(data_sources):
  return [
    {
      k.upper(): v
      for k, v in data_dict.items()
    } for data_dict in data_sources
  ]


def get_job_config(
  job_id: str, body: dict, creation_date: str
):
  name = body.get('name')
  desc = body.get('description')
  data_sources = process_data_sources(body.get('dataSources'))
  target = body.get('target')
  classes = body.get('classes')
  rewards = body.get('rewards')
  dataset = body.get('dataset')
  plugin_config = {
    "SIGNATURE": "AI4E_END_TO_END_TRAINING",
    "INSTANCES": []
  }
  instance_config = {
    "INSTANCE_ID": job_id,
    "OBJECTIVE_NAME": name,
    "GENERAL_DETECTOR_OBJECT_TYPE": target,
    "CLASSES": classes_msg_to_dict(classes),
    "DESCRIPTION": desc,
    "DATA": {
      "SOURCES": data_sources
    },
    "REWARDS": rewards,
    "DATASET": dataset,
    "CREATION_DATE": creation_date
  }
  plugin_config["INSTANCES"].append(instance_config)
  return plugin_config


class Job:
  def __init__(self, session: Session, job_id: str, node_id: str, pipeline: str, signature: str, instance: str):
    self.session = session
    self.job_id = job_id
    self.instance_id = instance
    self.node_id = node_id
    self.pipeline = pipeline
    self.signature = signature

    self.objective_name = None
    self.description = None
    self.data_sources = []
    self.target = None
    self.classes = {}
    self.rewards = {}
    self.dataset = {}
    self.creation_date = None
    self.job_status = None

    self.data = {}
    self.crop_status = {
      'total_stats': {},
      'increment_history': [],
      'speed': 0,
      'lastDuration': 0
    }

    return

  def maybe_update_data(self, data):
    if not data.get('IS_STATUS', True):
      return
    self.data = data
    self.objective_name = data.get('OBJECTIVE_NAME', self.objective_name)
    self.description = data.get('DESCRIPTION', self.description)
    self.data_sources = data.get('DATA_SOURCES', self.data_sources)
    self.target = data.get('TARGET', self.target)
    self.rewards = data.get('REWARDS', self.rewards)
    self.dataset = data.get('DATASET', self.dataset)
    self.creation_date = data.get('CREATION_DATE', self.creation_date)
    self.classes = data.get('CLASSES', self.classes)
    self.job_status = data.get('JOB_STATUS', self.job_status)

    self.crop_status['total_stats'] = data.get('COUNTS', self.crop_status['total_stats'])
    last_increment = data.get('CROP_INCREMENT')
    if last_increment is not None:
      self.crop_status['increment_history'].append(last_increment)
    self.crop_status['speed'] = data.get('CROP_SPEED', self.crop_status['speed'])
    self.crop_status['lastDuration'] = data.get('DURATION')

    return

  def get_data(self):
    return self.data

  def get_details(self):
    return {
      'name': self.objective_name,
      'description': self.description,
      'dataSources': self.data_sources,
      'target': self.target,
      'classes': classes_dict_to_msg(self.classes),
      'rewards': self.rewards,
      'dataset': self.dataset,
      'creationDate': self.creation_date
    }

  def to_msg(self):
    return {
      'id': self.job_id,
      'config': self.get_details()
    }

  def get_status(self):
    return {
      'crop': {
        'speed': self.crop_status['speed'],
        'history': self.crop_status['increment_history'],
        'duration': self.crop_status['lastDuration'],
      },
      'counts': self.crop_status['total_stats'],
      'job': self.to_msg(),
      'status': self.job_status
    }

  def __get_pipeline_and_instance(self):
    active_pipelines = self.session.get_active_pipelines(node_id=self.node_id)
    if active_pipelines is None:
      return None, None, f"Node_ID {self.node_id} not found"
    curr_pipeline = self.session.attach_to_pipeline(node_id=self.node_id, name=self.pipeline)
    if curr_pipeline is None:
      return None, None, f"Pipeline {self.pipeline} not found"
    curr_instance = curr_pipeline.attach_to_plugin_instance(
      signature=self.signature,
      instance_id=self.instance_id
    )
    return curr_pipeline, curr_instance, ""

  def send_instance_command(self, **kwargs):
    pipeline, instance, error = self.__get_pipeline_and_instance()
    if error != "":
      return False, error
    command_kwargs = {
      k.upper(): v
      for k, v in kwargs.items()
    }
    instance.send_instance_command(command_kwargs)
    return True, "Command sent successfully"

  def stop_acquisition(self):
    pipeline, instance, error = self.__get_pipeline_and_instance()
    if error != "" and error is not None:
      self.session.P(f'Error: {error} for {self.job_id} {self.pipeline} {self.instance_id}')
      return False, error
    instance.update_instance_config({"FORCE_TERMINATE_COLLECT": True})
    pipeline.deploy()
    return True, "Successfully stopped acquisition for job"


# endclass Job


class AI4E_CONSTANTS:
  RELEVANT_PLUGIN_SIGNATURES = ["ai4e_crop_data",]
  AVAILABLE_DATA_SOURCES = ['VideoStream', 'VideoFile']
  AVAILABLE_ARCHITECTURES = {
    'BASIC_CLASSIFIER': "Small architecture. The training will be faster, but the accuracy may be lower.",
    'ADVANCED_CLASSIFIER': "More complex architecture. The training will be slower, but the accuracy may be higher.",
  }
  FIRST_STAGE_CLASSES = [
  "person",
  "bicycle",
  "car",
  "motorcycle",
  "airplane",
  "bus",
  "train",
  "truck",
  "boat",
  "traffic light",
  "fire hydrant",
  "stop sign",
  "parking meter",
  "bench",
  "bird",
  "cat",
  "dog",
  "horse",
  "sheep",
  "cow",
  "elephant",
  "bear",
  "zebra",
  "giraffe",
  "backpack",
  "umbrella",
  "handbag",
  "tie",
  "suitcase",
  "frisbee",
  "skis",
  "snowboard",
  "sports ball",
  "kite",
  "baseball bat",
  "baseball glove",
  "skateboard",
  "surfboard",
  "tennis racket",
  "bottle",
  "wine glass",
  "cup",
  "fork",
  "knife",
  "spoon",
  "bowl",
  "banana",
  "apple",
  "sandwich",
  "orange",
  "broccoli",
  "carrot",
  "hot dog",
  "pizza",
  "donut",
  "cake",
  "chair",
  "couch",
  "potted plant",
  "bed",
  "dining table",
  "toilet",
  "tv",
  "laptop",
  "mouse",
  "remote",
  "keyboard",
  "cell phone",
  "microwave",
  "oven",
  "toaster",
  "sink",
  "refrigerator",
  "book",
  "clock",
  "vase",
  "scissors",
  "teddy bear",
  "hair drier",
  "toothbrush"
]



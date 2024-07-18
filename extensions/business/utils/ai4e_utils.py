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
  def __init__(self, job_id: str, node_id: str, pipeline: str, signature: str, instance: str):
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

    self.data = {}

    return

  def update_data(self, data):
    self.data = data
    self.objective_name = data.get('OBJECTIVE_NAME', self.objective_name)
    self.description = data.get('DESCRIPTION', self.description)
    self.data_sources = data.get('DATA_SOURCES', self.data_sources)
    self.target = data.get('TARGET', self.target)
    self.rewards = data.get('REWARDS', self.rewards)
    self.dataset = data.get('DATASET', self.dataset)
    self.creation_date = data.get('CREATION_DATE', self.creation_date)

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

  # def __get_pipeline_and_instance(self, sess: Session):
  #   active_pipelines = sess.get_active_pipelines(node_id=self.node_id)
  #   if active_pipelines is None:
  #     return None, None, f"Node_ID {self.node_id} not found"
  #   curr_pipeline = sess.attach_to_pipeline(node_id=self.node_id, name=self.pipeline)
  #   if curr_pipeline is None:
  #     return None, None, f"Pipeline {self.pipeline} not found"
  #   for instance_obj in curr_pipeline.lst_plugin_instances:
  #     print(f'{instance_obj.signature} - {instance_obj.instance_id}')
  #   curr_instance = curr_pipeline.attach_to_plugin_instance(
  #     signature=self.signature,
  #     instance_id=self.instance_id
  #   )
  #   return curr_pipeline, curr_instance, ""
  #
  # def stop_acquisition(self, sess: Session):
  #   pipeline, instance, error = self.__get_pipeline_and_instance(sess)
  #   if error != "" and error is not None:
  #     print(f'Error: {error} for {self.job_id} {self.pipeline} {self.instance_id}')
  #     return False, error
  #   instance.update_instance_config({"FORCE_TERMINATE_COLLECT": True})
  #   pipeline.deploy()
  #   return True, "Successfully stopped acquisition for job"
  #
  # def stop_label(self, sess: Session):
  #   pipeline, instance, error = self.__get_pipeline_and_instance(sess)
  #   if error != "" and error is not None:
  #     print(f'Error: {error} for {self.job_id} {self.pipeline} {self.instance_id}')
  #     return
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



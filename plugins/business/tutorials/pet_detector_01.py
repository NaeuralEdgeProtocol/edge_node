from core.business.base import CVPluginExecutor as BasePlugin


PET_TYPES = ['cat', 'dog', 'bird', 'horse', 'mouse']


_CONFIG = {
  **BasePlugin.CONFIG,
  'AI_ENGINE': ['lowres_general_detector'],
  'OBJECT_TYPE': PET_TYPES,
  'META_TYPE_MAPPING': {
    'pet': PET_TYPES
  },
  'REPORT_PERIOD': 30,  # seconds
  'TIMELINE_SLOT': 60,  # seconds
  'HISTORY_PERIOD': 60 * 60 * 24,  # seconds
  "FOOD_ZONE": [
    0.8, 0.8, 1, 1
  ],
  "FOOD_ZONE_MIN_COVERAGE": 0.7,  # the minimum coverage of the food zone for a pet to be considered "eating"
  "MAX_DISTANCE": 30,  # pixels, the maximum centroid distance for a pet to be considered stationary
  "MIN_FRAMES": 5,  # the minimum number of frames for a pet to be considered stationary

  'VALIDATION_RULES': {
    **BasePlugin.CONFIG['VALIDATION_RULES'],
  },
}


class PetDetector01Plugin(BasePlugin):
  CONFIG = _CONFIG

  def on_init(self):
    super(PetDetector01Plugin, self).on_init()
    self.pet_state_queue = self.deque()
    self.pet_state_count = {
      'missing': 0,
      'sleep': 0,
      'play': 0,
      'eat': 0
    }
    self.timeline = self.deque(maxlen=self.compute_timeline_length())
    self.current_time_slot_count = {
      'missing': 0,
      'sleep': 0,
      'play': 0,
      'eat': 0
    }
    self.current_time_slot = self.get_current_timeline_slot()
    self.last_time_slot = self.current_time_slot
    return

  def get_current_timeline_slot(self):
    dt_now = self.datetime.now()
    timeline_slot = dt_now.second + 60 * dt_now.minute + 60 * 60 * dt_now.hour
    return timeline_slot // self.cfg_timeline_slot

  def compute_timeline_length(self):
    """
    Method for computing the length of the timeline.
    The timeline will contain the aggregated data for
    time slots of length cfg_timeline_slot for the last 24 hours.
    Returns
    -------
    int - the length of the timeline
    """
    day_seconds = 60 * 60 * 24
    return day_seconds // self.cfg_timeline_slot

  def clean_old_pet_states(self):
    """
    Method for cleaning the old pet states from the queue.
    """
    while len(self.pet_state_queue) > 0 and self.time() - self.pet_state_queue[0]['time'] > self.cfg_history_period:
      state = self.pet_state_queue.popleft()
      self.pet_state_count[state['state']] -= 1
    return

  def update_timeline(self, state):
    """
    Method for updating the timeline with the current state.
    In case the current time slot is different from the last one, the timeline will be updated.
    The timeline will contain the aggregated data for time slots of length cfg_timeline_slot for the last 24 hours.
    Parameters
    ----------
    state : str - the current state

    Returns
    -------

    """
    current_timeline_slot = self.get_current_timeline_slot()
    # If the current time slot is different from the last one, update the timeline
    if current_timeline_slot != self.current_time_slot:
      # Add the current time slot count to the timeline
      self.timeline.append(self.current_time_slot_count)
      # Add empty slots if needed
      n_empty_slots = current_timeline_slot - self.current_time_slot
      for _ in range(n_empty_slots - 1):
        self.timeline.append({
          'missing': 0,
          'sleep': 0,
          'play': 0,
          'eat': 0
        })
      # endfor empty_slots
      # Reset the current time slot count
      self.current_time_slot_count = {
        'missing': 0,
        'sleep': 0,
        'play': 0,
        'eat': 0
      }
      self.current_time_slot = current_timeline_slot
    # endif current_time_slot
    # Update the current time slot count
    self.current_time_slot_count[state] += 1
    return

  def maybe_send_timeline_payload(self):
    """
    Method for sending the timeline payload.
    The timeline will be sent if the current time slot is different from the last one.
    Returns
    -------

    """
    if self.current_time_slot == self.last_time_slot:
      return
    self.last_time_slot = self.current_time_slot
    self.add_payload_by_fields(timeline=list(self.timeline))
    return

  def add_pet_state(self, state):
    """
    Method for adding a pet state to the queue and maybe update the timeline.
    Parameters
    ----------
    state : str - the pet state to be added

    Returns
    -------

    """
    # Add the state to the queue
    self.pet_state_queue.append({
      'state': state,
      'time': self.time()
    })
    # Update the state count
    self.pet_state_count[state] += 1
    # Update the timeline
    self.update_timeline(state)
    return

  def get_food_zone_area(self):
    """
    Method for getting the absolute food zone area coordinates.
    Returns
    -------
    tuple - the absolute food zone area coordinates
    """
    img_shape = self.dataapi_image().shape
    food_zone_tlbr = [min(max(x, 0), 1) for x in self.cfg_food_zone]
    return (
      int(img_shape[0] * food_zone_tlbr[0]),
      int(img_shape[1] * food_zone_tlbr[1]),
      int(img_shape[0] * food_zone_tlbr[2]),
      int(img_shape[1] * food_zone_tlbr[3])
    )

  def get_pet_data(self, inf):
    """
    Method for processing the data for a single pet in the frame.
    The following data will be added:
    - TIME_IN_SLOT: the time the pet has been in the frame in the current time slot
    - TYPE: the most seen type for the pet
    Parameters
    ----------
    inf : dict
        The inference data for the pet

    Returns
    -------
    dict - the processed data for the pet
    """
    return {
      **inf,
      'TIME_IN_SLOT': min(self.cfg_report_period, inf[self.ct.TIME_IN_TARGET]),
      'TYPE': self.trackapi_most_seen_type(inf[self.ct.TRACK_ID], self.get_tracking_type(inf))
    }

  def get_pets_data(self, inferences):
    """
    Method for processing the data for all the pets in the frame.
    Parameters
    ----------
    inferences : list
        A list of inferences for the current frame

    Returns
    -------
    list - the processed data for all the pets in the frame
    """
    pets_data = []
    for inference in inferences:
      pets_data.append(self.get_pet_data(inference))
    return pets_data

  def _draw_witness_image(self, img, pets_data):
    """
    Method for drawing the witness image.
    Here will be drawn both the pets seen in the image and the food zone.
    Parameters
    ----------
    img : np.ndarray
        The image to be drawn
    pets_data : list
        A list of the processed data for all the pets in the frame

    Returns
    -------
    np.ndarray - the image with the pets and the food zone drawn
    """
    # 1. Draw the pets
    for pet_data in pets_data:
      t, l, b, r = pet_data[self.ct.TLBR_POS]
      most_seen_type = self.trackapi_most_seen_type(pet_data[self.ct.TRACK_ID], self.get_tracking_type(pet_data))
      img = self._painter.draw_detection_box(
        image=img,
        top=int(t), left=int(l), bottom=int(b), right=int(r),
        color=self.ct.GREEN,
        thickness=2,
        text=f'{pet_data["pet_state"]}|{most_seen_type}[{pet_data[self.ct.TRACK_ID]}]: {pet_data["TIME_IN_SLOT"]:.2f}'
      )
    # endfor pets_data
    # 2. Draw the food zone
    food_tlbr = self.get_food_zone_area()
    img = self._painter.draw_detection_box(
      image=img,
      top=food_tlbr[0], left=food_tlbr[1], bottom=food_tlbr[2], right=food_tlbr[3],
      color=self.ct.RED,
      thickness=2,
      text='Food Zone'
    )
    return img

  def in_food_zone(self, inf):
    """
    Method for checking if the pet is in the food zone.
    For the pet to be considered in the food zone, the area of intersection between its bounding box and
    the food area must be at least FOOD_ZONE_MIN_COVERAGE * food_area.
    Parameters
    ----------
    inf : dict - the inference data for the pet

    Returns
    -------
    bool - True if the pet is in the food zone, False otherwise
    """
    food_tlbr = self.get_food_zone_area()
    pet_tlbr = inf[self.ct.TLBR_POS]
    inter_area = self.gmt.box_intersection(pet_tlbr, food_tlbr)
    min_food_area = self.gmt.tlbr_area(food_tlbr) * self.cfg_food_zone_min_coverage
    return inter_area >= min_food_area

  def is_stationary(self, inf):
    """
    Method for checking if the pet is stationary.
    For the pet to be considered stationary it has to:
    - be in the frame for at least MIN_FRAMES frames
    - have a maximum distance from the first frame centroid to any other frame centroid of MAX_DISTANCE pixels
    Parameters
    ----------
    inf : dict
        The inference data for the pet
    Returns
    -------
    bool - True if the pet is stationary, False otherwise
    """
    # Firstly, get the number of frames the pet has been in the frame
    life_span = self.trackapi_class_count(
      object_type=self.get_tracking_type(inf),
      object_id=inf[self.ct.TRACK_ID],
      class_name='total'
    )
    if life_span < self.cfg_min_frames:
      return False
    # Secondly, check the maximum distance between the centroids
    max_movement = self.trackapi_max_movement(
      object_type=self.get_tracking_type(inf),
      object_id=inf[self.ct.TRACK_ID],
      steps=self.cfg_min_frames
    )
    return max_movement < self.cfg_max_distance

  def get_pet_state(self, inf):
    """
    Method for getting the state of the pet based on the inference data.
    Parameters
    ----------
    inf : dict
        The inference data for the pet

    Returns
    -------
    str - the state of the pet
    """
    if self.is_stationary(inf):
      if self.in_food_zone(inf):
        return 'eat'
      return 'sleep'
    return 'play'

  def add_state_for_pets(self, inferences):
    """
    Method for adding the state of the pet to the inference data.
    Parameters
    ----------
    inferences : list
        A list of inferences for the current frame
    Returns
    -------
    list - the updated list of inferences with the pet state added
    """
    for inf in inferences:
      inf['pet_state'] = self.get_pet_state(inf)
    return inferences

  def current_pet_state(self, inferences):
    """
    Method for evaluating the current state of the monitored pet. It can be one of the following:
    - missing, if the pet is not in the frame
    - sleep, if the pet is in the frame and has not moved for a certain period of time
    - eat, if the pet is in the frame, has not moved for a certain period of time and is in the food zone
    - play, if the pet is in the frame and is moving
    In case of multiple pet detections, the reported state is the one with the highest priority.
    The priority is as follows: play > eat > sleep > missing
    Parameters
    ----------
    inferences : list
        A list of inferences for the current frame
    Returns
    -------
    str - the current state of the pet
    """
    is_playing, is_eating, is_sleeping = False, False, False
    for inf in inferences:
      if inf['pet_state'] == 'play':
        is_playing = True
      elif inf['pet_state'] == 'eat':
        is_eating = True
      elif inf['pet_state'] == 'sleep':
        is_sleeping = True
    # endfor inferences
    return 'play' if is_playing else 'eat' if is_eating else 'sleep' if is_sleeping else 'missing'

  def _process(self):
    # Clean old pet states
    self.clean_old_pet_states()
    # Get the inferences
    inferences = self.dataapi_image_instance_inferences()
    # Add pet state for every pet
    inferences = self.add_state_for_pets(inferences)
    # Get the current pet state for the frame
    # (in case of multiple pets, the state with the highest priority is reported)
    state = self.current_pet_state(inferences)
    # Add the frame state to the statistics
    self.add_pet_state(state)
    # Maybe send timeline payload
    self.maybe_send_timeline_payload()

    # If the report period has not passed, do nothing
    if not self.cfg_demo_mode and self.time() - self.last_payload_time < self.cfg_report_period:
      return
    # Get the processed data for the pets in the frame
    pets_data = self.get_pets_data(inferences)
    # Get the witness image
    np_witness = self.get_witness_image(
      draw_witness_image_kwargs=dict(pets_data=pets_data)
    )
    # Create the payload
    payload = self._create_payload(
      img=np_witness,
      pets_data=pets_data,
      pet_state_count=self.pet_state_count,
      pet_state=state
    )
    return payload


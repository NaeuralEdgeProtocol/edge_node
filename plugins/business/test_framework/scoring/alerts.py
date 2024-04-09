from datetime import datetime
from core.utils.datetime_utils import add_microseconds_to_str_timedelta
from core.business.test_framework.base import BaseScoringPlugin

class AlertsScoringPlugin(BaseScoringPlugin):

  def __init__(self, **kwargs):
    super(AlertsScoringPlugin, self).__init__(**kwargs)
    return

  def startup(self):
    super().startup()
    return

  @property
  def cfg_seconds_threshold_1(self):
    return self.config.get('SECONDS_THRESHOLD_1', 0.5)

  @property
  def cfg_seconds_threshold_2(self):
    return self.config.get('SECONDS_THRESHOLD_2', 2)

  @property
  def cfg_seconds_threshold_3(self):
    return self.config.get('SECONDS_THRESHOLD_3', 3)

  def _scoring(self):
    total_score = 0
    y_true_raise = [x for x in self.y_true if x['ALERT'] == 'RAISE']
    y_true_lower = [x for x in self.y_true if x['ALERT'] == 'LOWER']

    for dct_hat_crt in self.y_hat:
      k_h = dct_hat_crt['TIMESTAMP']
      v_h = dct_hat_crt['ALERT']

      crt_score = -self.score_per_obs
      dt_h = datetime.strptime(k_h, "%H:%M:%S.%f")
      if v_h == 'RAISE':
        crt_y_true = y_true_raise
      elif v_h == 'LOWER':
        crt_y_true = y_true_lower
      else:
        crt_y_true = {}

      for dct_true_crt in crt_y_true:
        k_t = dct_true_crt['TIMESTAMP']
        k_t = add_microseconds_to_str_timedelta(k_t)
        dt_t = datetime.strptime(k_t, "%H:%M:%S.%f")
        _min, _max = min(dt_t, dt_h), max(dt_t, dt_h)
        delta = _max - _min
        if delta.seconds <= self.cfg_seconds_threshold_1:
          crt_score = self.score_per_obs
          break
        elif self.cfg_seconds_threshold_1 < delta.seconds <= self.cfg_seconds_threshold_2:
          crt_score = self.score_per_obs / 5
          break
        elif self.cfg_seconds_threshold_2 < delta.seconds <= self.cfg_seconds_threshold_3:
          crt_score = 0
          break
        #endif
      #endfor
      total_score += crt_score
    #endfor

    return total_score

if __name__ == '__main__':

  yt = [
    {"TIMESTAMP" : "0:00:10", "ALERT" : "RAISE"},
    {"TIMESTAMP" : "0:00:15", "ALERT" : "LOWER"},
    {"TIMESTAMP" : "0:00:24", "ALERT" : "RAISE"},
    {"TIMESTAMP" : "0:00:44", "ALERT" : "LOWER"},
    {"TIMESTAMP" : "0:01:12", "ALERT" : "RAISE"},
    {"TIMESTAMP" : "0:01:20", "ALERT" : "LOWER"},
  ]

  yh = [
        {
            "ALERT": "RAISE",
            "TIMESTAMP": "0:00:24.240000"
        },
        {
            "ALERT": "LOWER",
            "TIMESTAMP": "0:00:35.400000"
        },
        {
            "ALERT": "RAISE",
            "TIMESTAMP": "0:01:00.280000"
        },
        {
            "ALERT": "LOWER",
            "TIMESTAMP": "0:01:04.640000"
        },
        {
            "ALERT": "RAISE",
            "TIMESTAMP": "0:01:12.200000"
        },
        {
            "ALERT": "LOWER",
            "TIMESTAMP": "0:01:23.880000"
        }
    ]


  from core import Logger
  log = Logger(lib_name='TST', base_folder='.', app_folder='_local_cache', TF_KERAS=False)

  p = AlertsScoringPlugin(log=log, y_true_src=yt)
  s = p.score(payload={'Y_HAT' : yh}, config={'MAX_SCORE' : 100})
  print(s)

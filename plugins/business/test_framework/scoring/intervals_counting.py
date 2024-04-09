from core.business.test_framework.base import BaseScoringPlugin
from datetime import datetime

class IntervalsCountingScoringPlugin(BaseScoringPlugin):

  def __init__(self, **kwargs):
    super(IntervalsCountingScoringPlugin, self).__init__(**kwargs)
    return

  def startup(self):
    super().startup()
    return

  @property
  def cfg_count_deviation(self):
    return self.config.get('COUNT_DEVIATION', 1)

  def _scoring(self):
    if len(self.y_true) != len(self.y_hat):
      msg = "Could not score because len(y_true) != len(y_hat)"
      self.exceptions.append(msg)
      self.P(msg, color='r')
      return -100

    total_score = 0
    for i in range(len(self.y_true)):
      y_true_i = self.y_true[i]
      y_hat_i = self.y_hat[i]
      start_true_i = datetime.strptime(y_true_i["START"], "%H:%M:%S")
      end_true_i = datetime.strptime(y_true_i["END"], "%H:%M:%S")
      start_hat_i = datetime.strptime(y_hat_i["START"], "%H:%M:%S")
      end_hat_i = datetime.strptime(y_hat_i["END"], "%H:%M:%S")
      err = False

      if i < len(self.y_true) - 1:
        if start_true_i != start_hat_i or end_true_i != end_hat_i:
          err = True
      else:
        if start_true_i != start_hat_i:
          err = True
      #endif

      if err:
        msg = "Could not score (mismatches between y_true and y_hat)"
        self.exceptions.append(msg)
        self.P(msg, color='r')
        return -100
      #endif

      crt_score = -self.score_per_obs
      diff = abs(y_true_i["COUNT"] - y_hat_i["COUNT"])
      if diff < self.cfg_count_deviation:
        crt_score = self.score_per_obs
      elif self.cfg_count_deviation <= diff < 2 * self.cfg_count_deviation:
        crt_score = self.score_per_obs / 2
      #endif

      total_score += crt_score
    #endfor

    return total_score

if __name__ == '__main__':

  yt = [
    {"START" : "0:00:00", "END" : "0:00:30", "COUNT" : 7},
    {"START" : "0:00:30", "END" : "0:01:00", "COUNT" : 4},
    {"START" : "0:01:00", "END" : "0:01:30", "COUNT" : 10},
    {"START" : "0:01:30", "END" : "0:02:00", "COUNT" : 10},
    {"START" : "0:02:00", "END" : "0:02:14", "COUNT" : 3},
  ]


  yh = [
    {"START" : "0:00:00", "END" : "0:00:30", "COUNT" : 10},
    {"START" : "0:00:30", "END" : "0:01:00", "COUNT" : 10},
    {"START" : "0:01:00", "END" : "0:01:30", "COUNT" : 10},
    {"START" : "0:01:30", "END" : "0:02:00", "COUNT" : 10},
    {"START" : "0:02:00", "END" : "0:02:14", "COUNT" : 10},
  ]

  from core import Logger
  log = Logger(lib_name='TST', base_folder='.', app_folder='_local_cache', TF_KERAS=False)

  p = IntervalsCountingScoringPlugin(log=log, y_true_uri=yt)
  s = p.score(payload={'Y_HAT' : yh}, config=dict(MAX_SCORE=100, SECONDS_THRESHOLD=1))
  print(s)

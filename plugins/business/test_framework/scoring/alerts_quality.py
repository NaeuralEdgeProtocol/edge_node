import numpy as np

from datetime import datetime
from collections import defaultdict
from core.utils.datetime_utils import add_microseconds_to_str_timedelta
from core.business.test_framework.base import BaseScoringPlugin


class AlertsQualityScoringPlugin(BaseScoringPlugin):

  def __init__(self, **kwargs):
    super(AlertsQualityScoringPlugin, self).__init__(**kwargs)
    return

  def startup(self):
    super().startup()
    return

  def date_to_idx(self, ts):
    if type(ts) == str:
      ts = add_microseconds_to_str_timedelta(ts)
      ts = datetime.strptime(ts, "%H:%M:%S.%f")

    return ts.hour * 3600 + ts.minute * 60 + ts.second

  def timestamps_to_mask(self, y, total_seconds):
    mask = np.zeros(total_seconds)
    for data in y:
      idx = self.date_to_idx(data['TIMESTAMP'])
      if data['ALERT'] == 'RAISE':
        mask[idx] += 1
      elif data['ALERT'] == 'LOWER':
        mask[idx] -= 1
    return mask

  def timestamps_to_mask_intervals(self, y, total_seconds):
    intervals = []
    last_raised = None

    for data in y:
      idx = self.date_to_idx(data['TIMESTAMP'])
      if data['ALERT'] == 'RAISE':
        last_raised = idx
      elif data['ALERT'] == 'LOWER':
        if last_raised is None:
          last_raised = 0
        intervals.append((last_raised, idx))
        last_raised = None
      # endif
    # endfor
    if last_raised is not None:
      # the last raised alert was not lowered so we have an
      # interval from last_raised till the end of the movie
      intervals.append((last_raised, total_seconds - 1))

    return intervals

  def intersecting_intervals(self, A, B):
    """
    Method for computing if to intervals A=[lA, rA] and B=[lB, rB] overlap
    """
    return min(A[1], B[1]) >= max(A[0], B[0])

  def free_intervals(self, intervals1, intervals2):
    """
    TODO: decide in what mixin/utils should this be moved
    Method for computing what intervals from intervals2 are not
    overlapped with at least one interval from intervals1
    """
    return [
      not any(self.intersecting_intervals(a, b) for b in intervals1)
      for a in intervals2
    ]

  def count_free_intervals(self, intervals1, intervals2):
    return sum(self.free_intervals(intervals1=intervals1, intervals2=intervals2))

  def total_seconds_free_intervals(self, intervals1, intervals2):
    """
    Method for computing the sum of seconds covered by intervals from
    intervals2 are not overlapped with at least one interval from intervals1
    """
    return sum(
      x[1] - x[0] + 1 for x in np.array(intervals2)[self.free_intervals(
        intervals1=intervals1,
        intervals2=intervals2
      )]
    )

  def get_mask_size(self, y_true, y_hat):
    y_true_ts = [
      datetime.strptime(
        add_microseconds_to_str_timedelta(x['TIMESTAMP']),
        "%H:%M:%S.%f"
      )
      for x in y_true
    ]
    y_hat_ts = [
      datetime.strptime((x['TIMESTAMP']), "%H:%M:%S.%f")
      for x in y_hat
    ]

    all_ts = y_true_ts + y_hat_ts

    if len(all_ts) < 1:
      return 1

    return self.date_to_idx(max(all_ts)) + 1

  def _scoring(self):
    # total_seconds = int(np.ceil(self.owner.limited_data_duration)) + 1
    total_seconds = self.get_mask_size(y_true=self.y_true, y_hat=self.y_hat)

    true_mask = self.timestamps_to_mask(y=self.y_true, total_seconds=total_seconds)
    pred_mask = self.timestamps_to_mask(y=self.y_hat, total_seconds=total_seconds)

    true_intervals = self.timestamps_to_mask_intervals(y=self.y_true, total_seconds=total_seconds)
    pred_intervals = self.timestamps_to_mask_intervals(y=self.y_hat, total_seconds=total_seconds)

    # total number of seconds predicted alerts that do not intersect with any ground truth alerts
    false_alerts_total_seconds = self.total_seconds_free_intervals(
      intervals1=true_intervals, intervals2=pred_intervals
    )
    # ground truth alerts that do not intersect with any predicted alerts
    missed_alerts_cnt = self.count_free_intervals(
      intervals1=pred_intervals, intervals2=true_intervals
    )

    # here we use the Difference Array technique in order to
    # determine in which second we have a predicted alert raised
    # and in which second we have a true alert raised
    for i in range(total_seconds - 1):
      true_mask[i + 1] = true_mask[i] + true_mask[i + 1]
      pred_mask[i + 1] = pred_mask[i] + pred_mask[i + 1]

    total_mask = pred_mask + 2 * true_mask
    values, counts = np.unique(total_mask, return_counts=True)

    values = np.asarray((values, counts)).T
    freq = defaultdict(lambda: 0)
    for value, count in values:
      freq[value] = count

    acc = (freq[0] + freq[3]) / (sum(counts))
    score_dict = {
      '_FALSE_POSITIVE_COUNT': freq[1],
      '_FALSE_NEGATIVE_COUNT': freq[2],
      '_TRUE_POSITIVE_COUNT': freq[3],
      'MISSED_ALERTS': missed_alerts_cnt,
      'FALSE_ALERTS_TOTAL_SECONDS': false_alerts_total_seconds,
      'ACCURACY': acc
    }

    # total_score = 0
    # y_true_raise = [x for x in self.y_true if x['ALERT'] == 'RAISE']
    # y_true_lower = [x for x in self.y_true if x['ALERT'] == 'LOWER']
    #
    # for dct_hat_crt in self.y_hat:
    #   k_h = dct_hat_crt['TIMESTAMP']
    #   v_h = dct_hat_crt['ALERT']
    #
    #   crt_score = -self.score_per_obs
    #   dt_h = datetime.strptime(k_h, "%H:%M:%S.%f")
    #   if v_h == 'RAISE':
    #     crt_y_true = y_true_raise
    #   elif v_h == 'LOWER':
    #     crt_y_true = y_true_lower
    #   else:
    #     crt_y_true = {}
    #
    #   for dct_true_crt in crt_y_true:
    #     k_t = dct_true_crt['TIMESTAMP']
    #     k_t = add_microseconds_to_str_timedelta(k_t)
    #     dt_t = datetime.strptime(k_t, "%H:%M:%S.%f")
    #     _min, _max = min(dt_t, dt_h), max(dt_t, dt_h)
    #     delta = _max - _min
    #     if delta.seconds <= self.cfg_seconds_threshold_1:
    #       crt_score = self.score_per_obs
    #       break
    #     elif self.cfg_seconds_threshold_1 < delta.seconds <= self.cfg_seconds_threshold_2:
    #       crt_score = self.score_per_obs / 5
    #       break
    #     elif self.cfg_seconds_threshold_2 < delta.seconds <= self.cfg_seconds_threshold_3:
    #       crt_score = 0
    #       break
    #     #endif
    #   #endfor
    #   total_score += crt_score
    # #endfor

    return score_dict


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

  p = AlertsQualityScoringPlugin(log=log, y_true_src=yt)
  s = p.score(payload={'Y_HAT' : yh}, config={'MAX_SCORE' : 100})
  print(s)

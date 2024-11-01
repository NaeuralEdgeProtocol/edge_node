from naeural_core.business.test_framework.base import BaseScoringPlugin

class SimpleCountingScoringPlugin(BaseScoringPlugin):

  def __init__(self, **kwargs):
    super(SimpleCountingScoringPlugin, self).__init__(**kwargs)
    return

  def startup(self):
    super().startup()
    return

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
      count_true_i = y_true_i["COUNT"]
      count_hat_i = y_hat_i["COUNT"]
      error_margin_hat_i = y_hat_i["ERROR_MARGIN"]

      if error_margin_hat_i >= count_hat_i / 4:
        total_score -= self.score_per_obs
        continue

      if count_hat_i - error_margin_hat_i <= count_true_i <= count_hat_i + error_margin_hat_i:
        total_score += self.score_per_obs
      else:
        total_score -= self.score_per_obs
      #endif
    #endfor

    return total_score

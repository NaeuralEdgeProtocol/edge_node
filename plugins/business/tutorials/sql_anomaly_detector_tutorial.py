import pandas as pd

from core.business.base import CVPluginExecutor
from core.business.base.cv_plugin_executor import _CONFIG as BASE_CONFIG

# Basic anomaly detector model
from core.utils.multi_period_anomaly_model import BasicAnomalyModel

__VER__ = '0.1.0.0'

_CONFIG = {
  **BASE_CONFIG,
  ### Needed for sql-type plugin
  'RUN_WITHOUT_IMAGE': True,
  'NO_WITNESS': True,  # throws error if not set to true
  ###

  'ANOMALY_PRC': 0.01,
  'QUERY_NAME': '',

  'VALIDATION_RULES': {
    **BASE_CONFIG['VALIDATION_RULES'],
    'ANOMALY_PRC':{
      'TYPE': 'float'
    },
    'QUERY_NAME': {
      'TYPE': 'str'
    }
  }
}


class SQLAnomalyDetectorTutorialPlugin(CVPluginExecutor):
  CONFIG = _CONFIG
  def __init__(self, **kwargs):
    super(SQLAnomalyDetectorTutorialPlugin, self).__init__(**kwargs)

  def startup(self):
    # Method that defines logic to be run at startup. In our case we need to instantiate the model object
    super().startup()
    self.model = BasicAnomalyModel()
    return

  def _process(self):
    # get data through the data api
    data = self.dataapi_struct_data()

    if isinstance(data, pd.DataFrame):
      # csv data capture
      df_data = data
    else:
      # sql data capture
      df_data = data[self.cfg_query_name]
    #endif

    # The anomaly detector model requires data to have the shape (datapoints, features). As our data is a simple
    #   timeseries we need to add another dim. From (datapoints) to (datapoints, 1)
    np_data = df_data.vals.to_numpy().reshape(-1,1)

    # Fit the model and get the anomalies
    self.model.fit(
      np_data,
      prc=self.cfg_anomaly_prc
    )
    anomalies = self.model.predict(
      np_data
    )

    # Format the data so that is more readable
    anomalies_datapoints = df_data[anomalies]
    lst_anomalies = [
      {
        'value': x[1]['vals'],
        'datetime': self.datetime.strftime(x[1]['timestamps'], '%Y/%m/%d_%H:%M')
      }
      for x in anomalies_datapoints.iterrows()
    ]

    # Create a payload and return
    payload = self._create_payload(
      anomalies=lst_anomalies
    )

    return payload
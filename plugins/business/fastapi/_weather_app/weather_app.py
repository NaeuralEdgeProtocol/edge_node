from core.business.base.web_app import FastApiWebAppPlugin

__VER__ = '0.1.0.0'

_CONFIG = {
  **FastApiWebAppPlugin.CONFIG,
  'USE_NGROK' : False,
  'NGROK_DOMAIN' : None,
  'NGROK_EDGE_LABEL' : None,

  'PORT' : 8080,

  'ASSETS' : '_weather_app',
  'JINJA_ARGS': {
    'html_files' : [
      {
        'name'  : 'index.html',
        'route' : '/',
        'method' : 'get'
      }
    ]
  },
  'VALIDATION_RULES': {
    **FastApiWebAppPlugin.CONFIG['VALIDATION_RULES'],
  },
}

class WCt:
  DATASET_CITIES_URL = "https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/geonames-all-cities-with-a-population-1000/exports/json?lang=en&timezone=Europe%2FHelsinki"
  DATASET_CITIES_FILENAME = '1000cities.json'
  USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.62 Safari/537.36"
  CITIES_FILE = '1000cities.json'
  K_COORD = 'coordinates'
  K_POP = 'population'
  K_NAME = 'name'
  K_ALT_NAMES = 'alternate_names'
  K_LON = 'lon'
  K_LAT = 'lat'
  K_GID = 'geoname_id'
  R_CITY = 'city'
  R_TEMP = 'temperature'
  R_COND = 'conditions'
  R_WIND = 'wind'
  R_SOURCE = 'source'
  R_ADDR = 'node'

class OMCt:
  OPENMETEO_REQ_URL = "https://api.open-meteo.com/v1/forecast?latitude={}&longitude={}&current=temperature_2m,wind_speed_10m,wind_direction_10m,cloud_cover"
  K_NOW = 'current'
  K_TEMP = 'temperature_2m'
  K_WINDSPEED = 'wind_speed_10m'
  K_WINDDIRECTION = 'wind_direction_10m'
  K_CLOUDCOVER = 'cloud_cover'
  SOURCE = 'Open-Meteo'
  REQ_SRC = 'open-meteo'

class MRCt:
  MR_URL = 'https://www.meteoromania.ro/wp-json/meteoapi/v2/starea-vremii'
  K_FEAT = 'features'
  K_PROP = 'properties'
  K_NAME = 'nume'
  K_TEMP = 'tempe'
  K_WINDSPEED = 'vant'
  K_CLOUDCOVER = 'nebulozitate'
  SOURCE = 'MeteoRomania'
  REQ_SRC = 'meteoromania'

class ACCCt:
  URL = "https://www.accuweather.com/web-api/three-day-redirect?lat={}&lon={}"
  CL_CURRENT = 'cur-con-weather-card__body'
  CL_TEMP = 'temp'
  CL_COND = 'phrase'
  CL_DETAIL = 'spaced-content detail'
  WIND_DETAIL = 'wind'
  SOURCE = 'AccuWeather'
  REQ_SRC = 'accuweather'

class BBCCt:
  URL = "https://www.bbc.com/weather/{}/today"
  CL_SLOT = 'wr-time-slot-container__slots'
  CL_TIME = 'wr-time-slot'
  CL_TEMP = 'wr-value--temperature--c'
  CL_WINDSPEED = 'wr-value--windspeed wr-value--windspeed--kph'
  CL_WINDDIRECTION = 'wr-wind-speed__description'
  CL_COND = 'wr-time-slot-secondary__weather-type-text gel-pica-bold'
  SOURCE = 'BBCWeather'
  REQ_SRC = 'bbcweather'

class GCt:
  URL = "https://www.google.com/search?q=weather+{}"
  TEMP_ID = "wob_tm"
  WIND_ID = "wob_ws"
  COND_ID = "wob_dc"
  SOURCE = 'Google'
  REQ_SRC = 'google'

class HTMLCt:
  DIV = 'div'
  SPAN = 'span'
  ID = 'id'

class WeatherAppPlugin(FastApiWebAppPlugin):

  CONFIG = _CONFIG

  def __init__(self, **kwargs):
    self.locations : dict = {} # city name -> tuple(longitude, latitude, geoid)
    super(WeatherAppPlugin, self).__init__(**kwargs)
    return

  def on_init(self, **kwargs):
    # Download a catalogue of cities and initialize location data.
    url=WCt.DATASET_CITIES_URL
    self.maybe_download(fn=WCt.CITIES_FILE,url=url, target='data')
    path = self.os_path.join(
      self.get_data_folder(),
      WCt.DATASET_CITIES_FILENAME
    )
    with open(path) as f:
      cities = self.json.load(f)

    for rec in cities:
      geoid = rec[WCt.K_GID]
      lon = rec[WCt.K_COORD][WCt.K_LON]
      lat = rec[WCt.K_COORD][WCt.K_LAT]
      pop = rec[WCt.K_POP]
      name_lst = rec.get(WCt.K_ALT_NAMES)

      if rec.get(WCt.K_ALT_NAMES) is None:
        name_lst = rec[WCt.K_NAME]
      else:
        name_lst = rec[WCt.K_ALT_NAMES] + [rec[WCt.K_NAME]]

      for name in name_lst:
        lst = self.locations.get(name.lower(), [])
        lst.append((lon, lat, pop, geoid))
        self.locations[name.lower()] = lst
      #endfor all location names
    #endfor all cities

    # Sort descending by population and drop the population data.
    # This allows us to search retrieve results for the most populated
    # city first, which is what people mean whey they type in the name.
    for name in self.locations.keys():
      loc_names = self.locations[name]
      loc_names = sorted(loc_names, key=lambda x: x[2], reverse=True)
      loc_names = [(x[0], x[1], x[3]) for x in loc_names]
      self.locations[name.lower()] = loc_names
    #endfor all names
    del cities

    super(WeatherAppPlugin, self).on_init(**kwargs)
    return

  def _direction_to_string(self, deg : int) -> str:
    """
    Converts an integer in degrees to a direction string
    (e.g. N, NE, E, SE, S, SW, W, NW).

    Parameters
    ----------
    deg : int, number of degrees

    Returns
    -------
    str, the direction string
    """
    deg = float(deg)
    deg = int(deg) % 360
    if deg <= 23 or deg >= 338:
      return 'N'
    if deg >=23 and deg <= 67:
      return 'NE'
    if deg >= 67 and deg <= 113:
      return 'E'
    if deg >= 113 and deg <= 158:
      return 'SE'
    if deg >=158 and deg <= 203:
      return 'S'
    if deg >= 203 and deg <= 248:
      return 'SW'
    if deg >= 248 and deg <= 292:
      return 'W'
    return 'NW'

  def _get_open_meteo(self, city : str) -> dict:
    """
    Get weather information from Open-Meteo.

    Parameters
    ----------
    city: str, the name of the city to get the information for

    Returns
    -------
    dict, containing keys as strings:
      'city' - The name of the city
      'temperature' - The temperature
      'conditions' - Weather conditions
      'wind' - Wind speed and direction
      'source' - source of data
    """
    # For now just use the first location, but really we should make
    # a request for each one.
    lon, lat, geoid = self.locations[city.lower()][0]

    headers = {'Accept': 'application/json'}
    url = OMCt.OPENMETEO_REQ_URL.format(lat, lon)
    r = self.requests.get(url, headers=headers)
    info = r.json()
    temp = info[OMCt.K_NOW][OMCt.K_TEMP]
    wind_speed = info[OMCt.K_NOW][OMCt.K_WINDSPEED]
    wind_direction = info[OMCt.K_NOW][OMCt.K_WINDDIRECTION]
    wind_direction = self._direction_to_string(wind_direction)
    wind = str(wind_speed) + ' km/h ' + str(wind_direction)
    conditions = 'Cloud cover ' + str(info[OMCt.K_NOW][OMCt.K_CLOUDCOVER]) + '%'
    return {
      WCt.R_CITY : city,
      WCt.R_TEMP : temp,
      WCt.R_COND : conditions,
      WCt.R_WIND : wind,
      WCt.R_SOURCE : OMCt.SOURCE,
      WCt.R_ADDR : self.ee_addr
    }

  def _get_meteoromania(self, city : str) -> dict:
    """
    Get weather information from MeteoRomania.

    Parameters
    ----------
    city: str, the name of the city to get the information for

    Returns
    -------
    dict, containing keys as strings:
      'city' - The name of the city
      'temperature' - The temperature
      'conditions' - Weather conditions
      'wind' - Wind speed and direction
      'source' - source of data
    """

    headers = {'Accept': 'application/json'}
    r = self.requests.get(MRCt.MR_URL, headers=headers)
    info = r.json()
    for feature in info[MRCt.K_FEAT]:
      if feature[MRCt.K_PROP][MRCt.K_NAME].lower().startswith(city.lower()):
        # Note this does not show rain/snow/etc, need to check fenomen_e for that.
        cond = feature[MRCt.K_PROP][MRCt.K_CLOUDCOVER]
        temp = feature[MRCt.K_PROP][MRCt.K_TEMP]
        wind = feature[MRCt.K_PROP][MRCt.K_WINDSPEED]
        return {
          WCt.R_CITY : city,
          WCt.R_TEMP : temp,
          WCt.R_COND : cond,
          WCt.R_WIND : wind,
          WCt.R_SOURCE : MRCt.SOURCE,
          WCt.R_ADDR : self.ee_addr
        }
    return None

  def _get_accuweather(self, city : str) -> dict:
    """
    Get weather information from AccuWeather.

    Parameters
    ----------
    city: str, the name of the city to get the information for

    Returns
    -------
    dict, containing keys as strings:
      'city' - The name of the city
      'temperature' - The temperature
      'conditions' - Weather conditions
      'wind' - Wind speed and direction
      'source' - source of data
    """

    # Note this might break and the right approach is to use the accuweather API.
    lon, lat, _ = self.locations[city.lower()][0]

    headers = {
      "user-agent": WCt.USER_AGENT
    }

    weather_url = ACCCt.URL.format(lat, lon)
    response = self.requests.get(weather_url, headers=headers)

    soup = self.bs4.BeautifulSoup(response.text, "html.parser")

    curr_w = soup.find(HTMLCt.DIV, class_=ACCCt.CL_CURRENT)
    temp = curr_w.find(HTMLCt.DIV, class_=ACCCt.CL_TEMP).text[:-2]
    cond = curr_w.find(HTMLCt.SPAN, class_=ACCCt.CL_COND).text
    detail = curr_w.find(HTMLCt.DIV, class_=ACCCt.CL_DETAIL)
    while detail is not None and detail.text.lower() != ACCCt.WIND_DETAIL:
      detail = detail.find_next()
    wind = 'Unknown' if detail is None else detail.find_next().text
    return {
      WCt.R_CITY : city,
      WCt.R_TEMP : temp,
      WCt.R_COND : cond,
      WCt.R_WIND : wind,
      WCt.R_SOURCE : ACCCt.SOURCE,
      WCt.R_ADDR : self.ee_addr
    }

  def _get_bbcweather(self, city : str) -> dict:
    """
    Get weather information from BBCWeather.

    Parameters
    ----------
    city: str, the name of the city to get the information for

    Returns
    -------
    dict, containing keys as strings:
      'city' - The name of the city
      'temperature' - The temperature
      'conditions' - Weather conditions
      'wind' - Wind speed and direction
      'source' - source of data
    """
    _, _, geoid = self.locations[city.lower()][0]

    headers = {
      "user-agent": WCt.USER_AGENT
    }
    weather_url = BBCCt.URL.format(geoid)
    response = self.requests.get(weather_url, headers=headers)

    soup = self.bs4.BeautifulSoup(response.text, "html.parser")
    slot_container = soup.find(class_=BBCCt.CL_SLOT)
    # There are more than one slots, but first one should be the
    # nearest to current time.
    # Find the correct time slot.
    slot = slot_container.find(class_=BBCCt.CL_TIME)
    temperature = slot.find(class_=BBCCt.CL_TEMP).text[:-1]
    windspeed = slot.find(class_=BBCCt.CL_WINDSPEED).text
    wdirection = slot.find(class_=BBCCt.CL_WINDDIRECTION).text.split()[-1]
    wind = windspeed + ' ' + wdirection
    conditions = slot.find(class_=BBCCt.CL_COND).text

    return {
      WCt.R_CITY : city,
      WCt.R_TEMP : temperature,
      WCt.R_COND : conditions,
      WCt.R_WIND : wind,
      WCt.R_SOURCE : BBCCt.SOURCE,
      WCt.R_ADDR : self.ee_addr
    }

  def _get_google(self, city : str) -> dict:
    """
    Get weather information from Google.

    Parameters
    ----------
    city: str, the name of the city to get the information for

    Returns
    -------
    dict, containing keys as strings:
      'city' - The name of the city
      'temperature' - The temperature
      'conditions' - Weather conditions
      'wind' - Wind speed and direction
      'source' - source of data
    """

    # Make sure this is an actual city so we don't end up making
    # random searches.
    if city.lower() not in self.locations.keys():
      return None
    lang = "en-US,en;q=0.5"
    headers = {
      "user-agent": WCt.USER_AGENT,
      "Accept-Language": lang,
      "Content-Language": lang
    }
    weather_url = GCt.URL.format(city)
    response = self.requests.get(weather_url, headers=headers)

    soup = self.bs4.BeautifulSoup(response.text, "html.parser")
    temperature = soup.find(HTMLCt.SPAN, attrs={HTMLCt.ID: GCt.TEMP_ID}).text
    wind = soup.find(HTMLCt.SPAN, attrs={HTMLCt.ID: GCt.WIND_ID}).text
    conditions = soup.find(HTMLCt.SPAN, attrs={HTMLCt.ID: GCt.COND_ID}).text
    return {
      WCt.R_CITY : city,
      WCt.R_TEMP : temperature,
      WCt.R_COND : conditions,
      WCt.R_WIND : wind,
      WCt.R_SOURCE : GCt.SOURCE,
      WCt.R_ADDR : self.ee_addr
    }

  @FastApiWebAppPlugin.endpoint
  def get_weather(self, city : str, source : str) -> dict:
    """
    Application entry point, returns the weather information for a city from
    the specified source.

    Parameters
    ----------
    city: str, the name of the city to get the information for
    source: str, name of the source from which to retrieve information. The
      current supported source are open-meteo, meteoromania, accuweather,
      bbcweather, and google.

    Returns
    -------
    dict, containing keys as strings:
      'city' - The name of the city
      'temperature' - The temperature
      'conditions' - Weather conditions
      'wind' - Wind speed and direction
      'source' - source of data

    In case of error returns None
    """

    try:
      if source.lower() == OMCt.REQ_SRC:
        return self._get_open_meteo(city)
      if source.lower() == MRCt.REQ_SRC:
        return self._get_meteoromania(city)
      if source.lower() == ACCCt.REQ_SRC:
        return self._get_accuweather(city)
      if source.lower() == BBCCt.REQ_SRC:
        return self._get_bbcweather(city)
      if source.lower() == GCt.REQ_SRC:
        return self._get_google(city)
    except Exception as _:
      pass
    return None

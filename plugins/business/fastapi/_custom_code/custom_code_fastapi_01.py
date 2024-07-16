"""
Plugin that can define custom endpoints and with code for a FastAPI web server.

The endpoints are specified in the `ENDPOINTS` configuration parameter, and should
look like this:

"ENDPOINTS": [ 
  {
    "NAME": "__ENDPOINT_NAME__",
    "METHOD": "__ENDPOINT_METHOD__", # Optional, default is "get", can be "post", "put", "delete", etc.
    "CODE": "__BASE64_ENCODED_ENDPOINT_CODE__",
    "ARGS": "__ENDPOINT_ARGS__",
  },
  ...
]

"""

from core.business.base.web_app import FastApiWebAppPlugin

__VER__ = '0.1.0.0'

_CONFIG = {
  **FastApiWebAppPlugin.CONFIG,
  'USE_NGROK': False,
  'NGROK_DOMAIN': None,
  'NGROK_EDGE_LABEL': None,

  'PORT': 8080,

  'ENDPOINTS': [],

  'ASSETS': '_custom_code',
  'JINJA_ARGS': {},
  'VALIDATION_RULES': {
    **FastApiWebAppPlugin.CONFIG['VALIDATION_RULES'],
  },
}


class CustomCodeFastapi01Plugin(FastApiWebAppPlugin):
  CONFIG = _CONFIG

  def __register_custom_code_endpoint(self, endpoint_name, endpoint_method, endpoint_base64_code, endpoint_arguments):
    # First check that i do not have any attribute with the same name
    import inspect
    existing_attribute_names = (name for name, _ in inspect.getmembers(self))
    if endpoint_name in existing_attribute_names:
      raise Exception("The endpoint name '{}' is already in use.".format(endpoint_name))

    custom_code_method, errors, warnings = self._get_method_from_custom_code(
      str_b64code=endpoint_base64_code,
      self_var='plugin',
      method_arguments=["plugin"] + endpoint_arguments
    )

    if errors is not None:
      raise Exception("The custom code failed with the following error: {}".format(errors))

    if len(warnings) > 0:
      self.P("The custom code generated the following warnings: {}".format("\n".join(warnings)))

    # Now register the custom code method as an endpoint
    import types
    setattr(self, endpoint_name, types.MethodType(FastApiWebAppPlugin.endpoint(custom_code_method, method=endpoint_method), self))
    return

  def on_init(self, **kwargs):
    for dct_endpoint in self.cfg_endpoints:
      endpoint_name = dct_endpoint.get('NAME', None)
      endpoint_method = dct_endpoint.get('METHOD', "get")
      endpoint_base64_code = dct_endpoint.get('CODE', None)
      endpoint_arguments = dct_endpoint.get('ARGS', None)
      self.__register_custom_code_endpoint(endpoint_name, endpoint_method, endpoint_base64_code, endpoint_arguments)

    super(CustomCodeFastapi01Plugin, self).on_init(**kwargs)
    return

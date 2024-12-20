class Processor():
  def __init__(self):
    self._on_init()
    return
  
  
  @staticmethod
  def payload_handler(signature="DEFAULT"):
    def decorator(f):
      f.__payload_signature__ = signature
      return f
    return decorator
  
  @property
  def handlers(self):
    return self.__handlers
  
  def _on_init(self):
    self.__handlers = {}
    # we get all the functions that start with on_payload_
    for name in dir(self):
      if callable(getattr(self, name)):
        func = getattr(self, name)
        if name.startswith("on_payload_"):
          signature = name.replace("on_payload_", "").upper()
          self.__handlers[signature] = getattr(self, name)
        # end if we have a on_payload_<signature>
        if hasattr(func, "__payload_signature__"):
          signature = func.__payload_signature__.upper()
          if signature == "DEFAULT":
            signature = self._signature.upper()
          self.__handlers[signature] = getattr(self, name)
        # end if we have a signature
      # end if callable
    # end for each name in dir  
  
  
  def process(self, payload):
    signature = payload.get("signature")
    data = payload.get("data")
    signature = signature.upper()
    if signature in self.__handlers:
      return self.__handlers[signature](data)
    return
  
  
  
class Plugin1(Processor):
  _signature = "PLUGIN_A"
  
  @Processor.payload_handler()
  def default_handler(self, data):
    print("Plugin_A: ", data)
    return
  
  @Processor.payload_handler("Plugin2")
  def other_handler(self, data):
    print("Plugin2: ", data)
    return
  
  
  def on_payload_signature_3(self, data):
    print("Plugin3: ", data)
    return
  
  
if __name__ == "__main__":
  p = Plugin1()
  p.process({"signature": "Plugin_a", "data": "Hello"})
  p.process({"signature": "Plugin2", "data": "World"})
  p.process({"signature": "Signature_3", "data": "!"})
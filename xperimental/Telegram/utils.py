import datetime
def log_with_color(message: str, color: str, boxed:bool = False, **kwargs) -> None:
  """
  Log a message with color.

  Args:
    message (str): The message to be logged.
    color (str): The color to be used for logging. Valid color options are "yellow", "red", "gray", "light", and "green".

  Returns:
    None
  """
  color_codes = {
    "y": "\033[93m",
    "r": "\033[91m",
    "gray": "\033[90m",
    "light": "\033[97m",
    "g": "\033[92m",
    "b": "\033[94m",
  }

  if color not in color_codes:
    color = "gray"

  end_color = "\033[0m"
  now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  prefix = f"[{now_str}] "
  
  if boxed:
    indent = 4
    str_indent = ' ' * indent
    spaces = 20
    line0 = '#' * (len(message) + spaces + 2)
    line1 = str_indent + line0
    line2 = str_indent + '#' + ' ' * (len(line0) - 2) + '#'
    line3 = str_indent + '#' + ' ' * (spaces // 2)  + message + ' ' * (spaces // 2) + '#'
    line4 = str_indent + '#' + ' ' * (len(line0) - 2) + '#'
    line5 = line1
    message =  f"{prefix}\n{line1}\n{line2}\n{line3}\n{line4}\n{line5}"
  else:
    message = f"{prefix}{message}"
  
  print(f"{color_codes.get(color, '')}{message}{end_color}", flush=True)
  return


if __name__ == '__main__':
  log_with_color('This is a test message', 'yellow')
  log_with_color('This is a test message', 'red')
  log_with_color('This is a test message', 'gray')
  log_with_color('This is a test message', 'light')
  log_with_color('This is a test message', 'green')
  log_with_color('This is a test message', 'blue')
  log_with_color('This is a muuuuuuuuuuuuuuuuuch looooooooooooooonger test message', 'red', boxed=True)
  log_with_color('This is a test message', 'green', boxed=True)

def match_template(json_data: dict, template: dict) -> bool:
  """
  Check if all keys (including subkeys) within the template can be found with the same values in the given JSON.

  Parameters
  ----------
  json_data : dict
    The JSON (dict) to check against the template.
  template : dict
    The template JSON (dict) containing the keys and values to match.

  Returns
  -------
  bool
    True if the JSON matches the template, False otherwise.
  """
  # Initialize the stack with the top-level dictionaries from json_data and template
  stack = [(json_data, template)]

  # Process each pair of current data and template dictionaries/lists from the stack
  while stack:
    current_data, current_tmpl = stack.pop()

    # Check if current_tmpl is a dictionary
    if isinstance(current_tmpl, dict):
      for key, value in current_tmpl.items():
        # If the key is not in current_data, return False
        if key not in current_data:
          return False

        # If the value in the template is a dictionary, add the corresponding pair to the stack
        if isinstance(value, dict):
          if not isinstance(current_data[key], dict):
            return False
          stack.append((current_data[key], value))

        # If the value in the template is a list, process each item in the list
        elif isinstance(value, list):
          if not isinstance(current_data[key], list):
            return False

          tmpl_list = value
          data_list = current_data[key]

          # For each item in the template list, ensure there is a matching item in the data list
          for tmpl_item in tmpl_list:
            matched = False
            for data_item in data_list:
              # If both are dictionaries, add them to the stack for further processing
              if isinstance(tmpl_item, dict) and isinstance(data_item, dict):
                stack.append((data_item, tmpl_item))
                matched = True
                break
              # If both are lists, add them to the stack for further processing
              elif isinstance(tmpl_item, list) and isinstance(data_item, list):
                stack.append((data_item, tmpl_item))
                matched = True
                break
              # If they are of the same type and equal, mark as matched
              elif tmpl_item == data_item:
                matched = True
                break
            # If no matching item is found, return False
            if not matched:
              return False

        # If the value is not a dictionary or list, directly compare the values
        elif current_data[key] != value:
          return False

    # Check if current_tmpl is a list
    elif isinstance(current_tmpl, list):
      for tmpl_item in current_tmpl:
        matched = False
        for data_item in current_data:
          # If both are dictionaries, add them to the stack for further processing
          if isinstance(tmpl_item, dict) and isinstance(data_item, dict):
            stack.append((data_item, tmpl_item))
            matched = True
            break
          # If both are lists, add them to the stack for further processing
          elif isinstance(tmpl_item, list) and isinstance(data_item, list):
            stack.append((data_item, tmpl_item))
            matched = True
            break
          # If they are of the same type and equal, mark as matched
          elif tmpl_item == data_item:
            matched = True
            break
        # If no matching item is found, return False
        if not matched:
          return False

  # If all checks passed, return True
  return True


if __name__ == '__main__':
  # Example JSON data
  json_data = {
    "ACTION": "UPDATE_PIPELINE_INSTANCE",
    "PAYLOAD": {
      "NAME": "",
      "SIGNATURE": "NET_MON_01",
      "INSTANCE_ID": "NET_MON_01_INST",
      "INSTANCE_CONFIG": {
        "TEST" : [
          1,
          2,
          {
            "A": 1,
            "B": 2
          },
          [
            {"C": 3},
            {"D": 4}
          ]
        ],
        "INSTANCE_COMMAND": {
          "node": "gts-ws",
          "request": "history",
          "options": {
            "step": 60,
            "time_window_hours": 12
          }
        }
      }
    },
    "EE_IS_ENCRYPTED": False,
    "EE_ID": "Goliath",
    "SESSION_ID": "SolisClient_bf2d",
    "INITIATOR_ID": "SolisClient_bf2d",
    "EE_SENDER": "0xai_A6IrUO8pNoZrezX7UhYSjD7mAhpqt-p8wTVNHfuTzg-G",
    "TIME": "2024-06-19 10:34:35.414871",
    "EE_SIGN": "MEUCIB8ld6lThBUGLf7SupLwtyR5M2xVb53QXHSNaDiMIW3dAiEAldJ7iuvtxNGRKn_PqLGHX0uYxN2GCjLvC--S-qLIQvU=",
    "EE_HASH": "73d9f948560fad8be98f0fb9387598b96e56c055be33e7a68d5db43f2428922c"
  }

  # Template 1: Simple match
  JSON_FILE = [
  {
    "ACTION": "UPDATE_PIPELINE_INSTANCE",
    "PAYLOAD": {
      "NAME": "",
      "SIGNATURE": "NET_MON_01",
      "INSTANCE_ID": "NET_MON_01_INST",
      "INSTANCE_CONFIG": {
        "INSTANCE_COMMAND": {
          "request": "history"
        }
      }
    }
  },

  # Template 2: Matching nested dictionary within list
  {
    "ACTION": "UPDATE_PIPELINE_INSTANCE",
    "PAYLOAD": {
      "NAME": "",
      "SIGNATURE": "NET_MON_01",
      "INSTANCE_ID": "NET_MON_01_INST",
      "INSTANCE_CONFIG": {        
        "TEST" : [
          {
            "A": 1,
          }
        ],
        "INSTANCE_COMMAND": {
          "request": "history",
        }
      }
    }
  },

  # Template 3: Mismatched value in nested dictionary
  {
    "ACTION": "UPDATE_PIPELINE_INSTANCE",
    "PAYLOAD": {
      "NAME": "",
      "SIGNATURE": "NET_MON_01",
      "INSTANCE_ID": "NET_MON_01_INST",
      "INSTANCE_CONFIG": {        
        "INSTANCE_COMMAND": {
          "request": "history",
          "TEST" : [
            {
              "A": 2,
            }
          ]
        }
      }
    }
  },
  

  # Template 4: Matching nested list within list
  {
    "ACTION": "UPDATE_PIPELINE_INSTANCE",
    "PAYLOAD": {
      "NAME": "",
      "SIGNATURE": "NET_MON_01",
      "INSTANCE_ID": "NET_MON_01_INST",
      "INSTANCE_CONFIG": {        
        "TEST" : [
          [
            {"C": 3}
          ]
        ],
        "INSTANCE_COMMAND": {
          "request": "history"
        }
      }
    }
  }
  ]

  # Test cases
  for template in JSON_FILE:
    print(match_template(json_data, template))  # Output should be: True, True, False, True

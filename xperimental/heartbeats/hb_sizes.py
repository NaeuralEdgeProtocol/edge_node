import pickle
import sys


def compute_hb_fields_sizes(
    db_path: str, add_keys=False, descending=True,
    ignore_keys=None, key_aliases=None
):
  hb_data = pickle.load(open(db_path, 'rb+'))
  total_sizes = {}
  ignore_keys = ignore_keys or []
  key_aliases = key_aliases or {}

  for addr, info in hb_data.items():
    for hb in info:
      for k, v in hb.items():
        if k in ignore_keys:
          continue
        used_key = key_aliases.get(k, k)
        if used_key not in total_sizes:
          total_sizes[used_key] = 0
        current_size = (sys.getsizeof(v) + sys.getsizeof(used_key)) if add_keys else sys.getsizeof(v)
        total_sizes[used_key] += current_size
      # endfor each key in hb
    # endfor each hb in info
  # endfor each addr in hb_data

  lst_vals = [(k, v) for k, v in total_sizes.items()]
  sorted_vals = sorted(lst_vals, key=lambda x: x[1], reverse=descending)
  return {
    k: v for k, v in sorted_vals
  }


if __name__ == '__main__':
  db_path = r'C:\repos\edge_node\_local_cache\_data\network_monitor\db.pkl'
  sizes = compute_hb_fields_sizes(
    db_path=db_path,
    add_keys=True,
    ignore_keys=['TEMPERATURE_INFO'],
    key_aliases={
      # 'TEMPERATURE_INFO': 'TEMP_INF'
    }
  )
  for k, v in sizes.items():
    print(f"{k}: {v}")
  total = sum([v for v in sizes.values()])
  print(f"Total: {total}")



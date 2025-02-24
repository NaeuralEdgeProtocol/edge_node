import gc
import random
import json
import hashlib
import itertools
from time import time
from copy import deepcopy
from collections import defaultdict, Counter


def get_random_address():
  return "".join([chr(random.randint(97, 122)) for _ in range(44)])


def create_mockup_availability_table_from_one_oracle(
    n_epochs: int, n_nodes: int, node_addresses: list = None,
    max_epoch_availability: int = 255
):
  """
  Create a mockup availability table for one oracle.
  Parameters
  ----------
  n_epochs : int
    The number of epochs to create the availability table for.
  n_nodes : int
    The number of nodes in each epoch.
  node_addresses: list
    A list of strings, each string representing a node address.
    If None, the addresses will be randomly generated.
  max_epoch_availability : int
    The maximum availability score for a node in an epoch.
    The availability score is a random integer between 0 and this value.

  Returns
  -------
  availability_table : dict
    A dictionary of dictionaries, where the first key is the epoch number,
    and the second key is the node address.
    The value represents the availability score of the node in the given epoch.
  """
  if node_addresses is None:
    # If no node addresses are provided, create them.
    # Each address will be a string of 44 random characters.
    node_addresses = [
      get_random_address()
      for _ in range(n_nodes)
    ]
  # endif node_addresses check

  availability_table = defaultdict(lambda: defaultdict(int))
  for epoch in range(n_epochs):
    for node_address in node_addresses:
      availability_table[epoch][node_address] = random.randint(0, max_epoch_availability)
    # endfor node_address
  # endfor epoch

  return availability_table


def create_mockup_availability_table_from_multiple_oracles(
    n_oracles: int, n_epochs: int, n_nodes: int,
    n_unique_availability_values: int,
    max_epoch_availability: int,
    return_frequency: bool = False
):
  """
  Create a mockup availability table for multiple oracles.
  Some oracles should have the same availability table.
  Parameters
  ----------
  n_oracles : int
    The number of oracles to create the availability tables for.
  n_epochs : int
    The number of epochs to create the availability table for.
  n_nodes : int
    The number of nodes in each epoch.
  n_unique_availability_values : int
    The number of unique availability tables to create.
  max_epoch_availability : int
    The maximum availability score for a node in an epoch.
    The availability score is a random integer between 0 and this value.
  return_frequency : bool
    If True, return the frequency of each availability table hash.

  Returns
  -------
  (availability_tables, frequencies) if return_frequency is True, else availability_tables, where:
  availability_tables : dict
    A dictionary of dictionaries, where the first key is the oracle address,
    the second key is the epoch number, and the third key is the node address.
    The value represents the availability score of the node in the given epoch.
  frequencies : dict
    A dictionary where the key is the index of the unique availability table,
    and the value is the number of oracles that have this availability table.
  """
  print(f"Creating mockup data for {n_oracles} oracles with {n_unique_availability_values} "
        f"unique availability tables in {n_epochs} epochs for {n_nodes} nodes.")
  # Create N_UNIQUE_AVAILABILITY_VALUES unique availability tables.
  # These tables will be assigned to N_ORACLES oracles, so that some
  # oracles will have the same availability table.
  unique_tables_from_oracles = [
    create_mockup_availability_table_from_one_oracle(
      n_epochs=n_epochs,
      n_nodes=n_nodes,
      max_epoch_availability=max_epoch_availability
    )
    for _ in range(n_unique_availability_values)
  ]

  print(f"Unique availability tables created: {len(unique_tables_from_oracles)}.")
  # Create oracle addresses
  oracle_addresses = [get_random_address() for _ in range(n_oracles)]

  # Create the final mockup data.
  # Each oracle will have an availability table from unique_tables_from_oracles.
  final_mockup_data = {}
  frequencies = {}
  for oracle_addresses in oracle_addresses:
    choice_index = random.randint(0, n_unique_availability_values - 1)
    final_mockup_data[oracle_addresses] = deepcopy(unique_tables_from_oracles[choice_index])
    if choice_index not in frequencies:
      frequencies[choice_index] = 0
    # endif choice_index check
    frequencies[choice_index] += 1
  # endfor oracle_addresses

  print(f"Mockup data created for {n_oracles} oracles.")
  return (final_mockup_data, frequencies) if return_frequency else final_mockup_data


def hash_method1(availability_table):
  return hash(frozenset((k, hash(frozenset(v.items()))) for k, v in availability_table.items()))


def hash_method2(availability_table):
  return hashlib.sha256(bytes(json.dumps(availability_table), 'utf-8')).hexdigest()


def hash_frequency_method1(oracle_hashes):
  return Counter(oracle_hashes.values())


def hash_frequency_method2(oracle_hashes):
  dct_frequency = defaultdict(int)
  for hash_value in oracle_hashes.values():
    dct_frequency[hash_value] += 1
  return dct_frequency


def hash_frequency_method3(oracle_hashes):
  dct_frequency = {}
  for hash_value in oracle_hashes.values():
    dct_frequency[hash_value] = dct_frequency.get(hash_value, 0) + 1
  return dct_frequency


def same_frequencies(frequencies1, frequencies2):
  if len(frequencies1) != len(frequencies2):
    return False
  sorted_values_1 = sorted(frequencies1.values())
  sorted_values_2 = sorted(frequencies2.values())
  return sorted_values_1 == sorted_values_2


def compute_requested_availability(
    gathered_availability_table: dict,
    hash_method: callable,
    hash_frequency_method: callable,
    frequencies: dict
):
  """
  Compute the availability table for the requested epochs from the
  gathered availability tables sent by oracles.
  Parameters
  ----------
  gathered_availability_table : dict
    A dictionary of dictionaries, where the first key is the oracle address,
    the second key is the epoch number, and the third key is the node address.
    The value represents the availability score of the node in the given epoch.
  hash_method : callable
    A hash method to use for frequency analysis.
  hash_frequency_method : callable
    A method to compute the frequency of each hash.
  frequencies : dict
    A dictionary where the key is the index of the unique availability table,
    and the value is the number of oracles that have this availability table.

  Returns
  -------
  (success, elapsed) : tuple, where:
  success :bool
    True if the computed frequency is correct, False otherwise.
  elapsed : float
    The time it took to compute the requested availability.
  """
  start_time = time()
  # Compute the hash for every oracle table for frequency analysis.
  oracle_hashes = {
    oracle_address: hash_method(availability_table)
    for oracle_address, availability_table in gathered_availability_table.items()
  }

  # Compute the frequency of each hash.
  oracle_hashes_frequency = hash_frequency_method(oracle_hashes)

  # Find the most frequent hash.
  most_frequent_hash = max(oracle_hashes_frequency)

  # Find the oracles with the most frequent hash.
  availability_candidates = [
    oracle_address
    for oracle_address, hash_value in oracle_hashes.items()
    if hash_value == most_frequent_hash
  ]
  elapsed = time() - start_time
  success = same_frequencies(oracle_hashes_frequency, frequencies)

  # Select a random oracle from the candidates.
  selected_candidate = random.choice(availability_candidates)
  selected_availability = gathered_availability_table[selected_candidate]
  return success, elapsed


def main():
  # Creating mockup data.
  N_ORACLES = 100
  N_NODES = 1000
  N_EPOCHS = 500
  MAX_EPOCH_AVAILABILITY = 255

  N_UNIQUE_AVAILABILITY_VALUES = 30

  aggregated_availability_table, frequencies = create_mockup_availability_table_from_multiple_oracles(
    n_oracles=N_ORACLES,
    n_epochs=N_EPOCHS,
    n_nodes=N_NODES,
    n_unique_availability_values=N_UNIQUE_AVAILABILITY_VALUES,
    max_epoch_availability=MAX_EPOCH_AVAILABILITY,
    return_frequency=True
  )

  hash_methods = [
    hash_method1,
    hash_method2
  ]
  hash_frequency_methods = [
    hash_frequency_method1,
    hash_frequency_method2,
    hash_frequency_method3
  ]

  timings = {}
  N_TESTS = 10
  for _ in range(N_TESTS):
    print(f"Test {_ + 1}/{N_TESTS}")
    random.shuffle(hash_methods)
    random.shuffle(hash_frequency_methods)

    # Testing all the configurations.
    for element in itertools.product(hash_methods, hash_frequency_methods):
      gc.collect()
      hash_method, hash_frequency_method = element
      print(f"Testing hash method: {hash_method.__name__}, Frequency method: {hash_frequency_method.__name__}")
      success, elapsed = compute_requested_availability(
        gathered_availability_table=aggregated_availability_table,
        hash_method=hash_method,
        hash_frequency_method=hash_frequency_method,
        frequencies=frequencies
      )
      timings_key = f"{hash_method.__name__}___{hash_frequency_method.__name__}"
      if timings_key not in timings:
        timings[timings_key] = {
          "success": [],
          "elapsed": []
        }
      timings[timings_key]["success"].append(success)
      timings[timings_key]["elapsed"].append(elapsed)
      print(f"Hash method: {hash_method.__name__}, Frequency method: {hash_frequency_method.__name__}")
      print(f"Success: {success}, Elapsed: {elapsed:.6f} seconds")
      print("-" * 80)
    # endfor element
  # endfor N_TESTS

  print("Timings:")
  for key, value in timings.items():
    msg = f"  Configuration: {key}\n"
    msg += f"    Success rate: {sum(value['success'])}/{N_TESTS}\n"
    msg += f"    Average elapsed: {sum(value['elapsed']) / N_TESTS:.6f} seconds\n"
    msg += "-" * 80
    print(msg)
  return



if __name__ == '__main__':
  main()


#!/usr/bin/python3
import threading, ping3
import tty, sys, termios, signal, os
from time import sleep

ping3.EXCEPTIONS = True

# Bash color codes to highlight output
class bcolors:
  HEADER = '\033[95m'
  BLUE = '\033[94m'
  CYAN = '\033[96m'
  GREEN = '\033[92m'
  RED = '\033[91m'
  YELLOW = '\033[93m'
  BOLD = '\033[1m'
  UNDERLINE = '\033[4m'
  ENDC = '\033[0m'

# Print help info
def show_help():
  print("""multiping - simultaneously ping multiple hosts.

  parameters:
       Hostname or IP address of host (repeat this parameter as needed)
       timeout: -t or --timeout  The timeout value, in seconds, to set for each ping. (default is 0.25)
       repeat: -r or --repeat    The number of pings to send to each host.  0 means unlimited. (default 0)
  """)
  exit()

# Read command line arguments
#    -t, --timeout : The timeout value, in seconds, for each ping (default 0.25)
#    -r, --repeat  : The repeat (number of pings) to send to each host.  0 means unlimited.  (default 0)
def read_parameters():
  if len(sys.argv) == 1:
    show_help()
  args = sys.argv[1:]
  params = {"repeat":0, "timeout":0.25, "hosts":[]}
  next_arg = "host"
  for arg in args:
    if next_arg in ["repeat", "timeout"]:
      params[next_arg] = float(arg)
      next_arg = "host"
    elif arg in ["-h", "-?", "--help"]:
      show_help()
    elif arg in ["-t", "--timeout"]:
      next_arg = "timeout"
    elif arg in ["-r", "--repeat"]:
      next_arg = "repeat"
    else:
      params['hosts'].append(arg)
  return params

# For unlimited pings some sort of break is needed to stop the ping but not halt the program.  
# This allows a summary to display after the pings
# This threaded function will run in the background and monitor stdin for input.
# When the "q" key is pressed, the thread will terminate. 
# Active status of thread can be used to determine the need to halt pings.
def threaded_check_input():
  fd = termios.tcgetattr(sys.stdin)
  tty.setcbreak(sys.stdin)
  key = 0
  while key != 'q':
    key = sys.stdin.read(1)[0]
  termios.tcsetattr(sys.stdin, termios.TCSADRAIN, fd)

# For unlimited pings Ctrl-C is disabled.  Instead "q" should be used to stop the process.
# This handler function provides user feedback if they try to use Ctr-C to halt the ping process.
def handler(signum, frame):
  print('================ press "q" to quit. ==================')

# Function to ping an individual host.  This thread is meant to be threaded, to allow for multiple simultaneous pings.
#     host    - the host name/address to be pinged in this thread
#     result  - a list shared from the parent script.  This serves as a shared buffer to store ping results from threads to the main function.
#     index   - the position within the result list where output should be stored.
#     timeout - the timeout value to set on the ping.
def threaded_ping(host, result, index, timeout=0.25):
  try:
    t = ping3.ping(host, timeout=timeout) * 1000
    result[index] = f"{t:.2f} ms"
  except Exception as e:
    result[index] = str(e)
    if "timeout" in result[index]:
      result[index] = "timeout"
    elif "Unknown host" in result[index]:
      result[index] = "unknown host"

# Send one ping to each host in the hosts list and capture the results
#      hosts    - a list of hostnames/addresses to be pinged
#      timeout  - the timeout value in seconds for each ping.
def multiping_data(hosts, timeout=0.25):
  if not type(hosts) is list:
    raise Exception("Invalid type for \"hosts\" argument.  Type should be list.")
  results = [None] * len(hosts)
  threads = [None] * len(hosts)
  for idx in range(len(hosts)):
    threads[idx] = threading.Thread(target=threaded_ping, args=(hosts[idx], results, idx, timeout))
    threads[idx].start()
  sleep(timeout)
  while True in [thread.is_alive() for thread in threads]:
    sleep(0.01)
  return results

# Clean up ping data for display
def pretty_ping_data(pings, spacing):
  for idx in range(len(pings)):
    if ' ms' in pings[idx]:
      color = bcolors.GREEN
    else:
      color = bcolors.RED
    pings[idx] = f"{color}{pings[idx].rjust(spacing)}{bcolors.ENDC}"
  return pings

# The main multiping function.  
def multiping(hosts, repeat=0, timeout=0.25):
  spacing = max([len(host) for host in hosts] + [12]) +2
  if repeat == 0:
    signal.signal(signal.SIGINT, handler)
    thread_check = threading.Thread(target=threaded_check_input)
    thread_check.start()
    loop_check = lambda r: (r < repeat or repeat == 0) and thread_check.is_alive()
  else:
    loop_check = lambda r: (r < repeat or repeat == 0)
  n = 0
  drops = [0] * len(hosts)
  drops_set = [0] * len(hosts)
  while loop_check(n):
    pings = multiping_data(hosts, timeout)
    for idx in range(len(hosts)):
      if not " ms" in pings[idx]:
        drops[idx] += 1
        drops_set[idx] +=1
        if pings[idx] == "timeout": pings[idx] += f" - {drops_set[idx]}"
      else:
        drops_set[idx] = 0
    pings = pretty_ping_data(pings, spacing)
    print("".join(pings))
    print("".join([host.rjust(spacing) for host in hosts]), end="\r")
    n+=1
  print("")
  print("".join([f"{drop} drops".rjust(spacing) for drop in drops]))
  print(f"{n} pings sent per host with timeout set to {timeout}s.")

params = read_parameters()
multiping(hosts=params['hosts'], repeat=params['repeat'], timeout=params['timeout'])



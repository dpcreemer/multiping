#!/usr/bin/python3
import threading, ping3
import tty, sys, termios, signal, os
from time import sleep

ping3.EXCEPTIONS = True

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


class Check_Input_Thread(threading.Thread):
  def __init__(self, *args, **kwargs):
    super(Check_Input_Thread, self).__init__(*args, **kwargs)
    self._stop = threading.Event()

  def stop(self):
    print("stopping")
    self._stop.set()
  
  def stopped(self):
    print("checking for Stop")
    return self._stop.isSet()
  
  def run(self):
    fd = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin)
    key = 0
    while True:
      key = sys.stdin.read(1)[0]
      if key == 'q' or self.stopped():
        break
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, fd)

def read_parameters():
  args = sys.argv[1:]
  params = {"repeat":0, "timeout":0.25, "hosts":[]}
  next_arg = "host"
  for arg in args:
    if next_arg in ["repeat", "timeout"]:
      params[next_arg] = float(arg)
      next_arg = "host"
    elif arg in ["-t", "--timeout"]:
      next_arg = "timeout"
    elif arg in ["-r", "--repeat"]:
      next_arg = "repeat"
    else:
      params['hosts'].append(arg)
  return params

def handler(signum, frame):
  print('================ press "q" to quit. ==================')

def threaded_check_input():
  fd = termios.tcgetattr(sys.stdin)
  tty.setcbreak(sys.stdin)
  key = 0
  while key != 'q':
    key = sys.stdin.read(1)[0]
  termios.tcsetattr(sys.stdin, termios.TCSADRAIN, fd)

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

def pretty_ping_data(pings, spacing):
  for idx in range(len(pings)):
    if ' ms' in pings[idx]:
      color = bcolors.GREEN
    else:
      color = bcolors.RED
    pings[idx] = f"{color}{pings[idx].rjust(spacing)}{bcolors.ENDC}"
  return pings

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
  drops = [0] * len (hosts)
  while loop_check(n):
    pings = multiping_data(hosts, timeout)
    for idx in range(len(hosts)):
      if not " ms" in pings[idx]:
        drops[idx] += 1
    pings = pretty_ping_data(pings, spacing)
    print("".join(pings))
    print("".join([host.rjust(spacing) for host in hosts]), end="\r")
    n+=1
  print("")
  print("".join([f"{drop} drops".rjust(spacing) for drop in drops]))
  print(f"{n} pings sent per host.")

#multiping(sys.argv[1:])
params = read_parameters()
multiping(hosts=params['hosts'], repeat=params['repeat'], timeout=params['timeout'])



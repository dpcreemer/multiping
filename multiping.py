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

def threaded_check_input():
  fd = termios.tcgetattr(sys.stdin)
  tty.setcbreak(sys.stdin)
  key = 0
  while True:
    key = sys.stdin.read(1)[0]
    if key == 'q':
      break
  termios.tcsetattr(sys.stdin, termios.TCSADRAIN, fd)

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
  signal.signal(signal.SIGINT, handler)
  spacing = max([len(host) for host in hosts] + [12]) +2
  n=0
  thread_check = threading.Thread(target=threaded_check_input)
  thread_check.start()
  while n < repeat or repeat ==0:
    pings = multiping_data(hosts, timeout)
    pings = pretty_ping_data(pings, spacing)
    print("".join(pings))
    print("".join([host.rjust(spacing) for host in hosts]), end="\r")
    n+=1
    if not thread_check.is_alive(): break
  print("")

#multiping(sys.argv[1:])
params = read_parameters()
multiping(hosts=params['hosts'], repeat=params['repeat'], timeout=params['timeout'])



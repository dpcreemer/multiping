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

class Multiping:
  def __init__(self, hosts, timeout=0.25, repeat=0):
    self.__hosts = [None]
    self.__timeout = None
    self.__repeat = None
    self.__spacing = 12
    self.hosts = hosts
    self.timeout = timeout
    self.repeat = repeat
    self.results = [None] * self.host_count
    self.drops_active = [0] * self.host_count
    self.drops_total = [0] * self.host_count

  @property
  def hosts(self):
    return self.__hosts

  @hosts.setter
  def hosts(self, hosts):
    if not type(hosts) is list:
      raise Exception(f"Invalid type {type(hosts)} for hosts parameter.  Should be type List.")
    self.__hosts = hosts
    self.__spacing = max([len(host) for host in hosts] + [12])
  
  @property
  def timeout(self):
    return self.__timeout
  
  @timeout.setter
  def timeout(self, timeout):
    try: 
      self.__timeout = float(timeout)
    except:
      raise Exception(f"Invalid value {timeout} for timeout.  Should be a number.")
  
  @property 
  def repeat(self):
    return self.__repeat
  
  @repeat.setter
  def repeat(self, repeat):
    try:
      self.__repeat = int(repeat)
    except:
      raise Exception(f"Invalid value {repeat} for repeat.  Should be an integer. (0 means unlimited).")
  
  @property
  def host_count(self):
    return len(self.hosts)

  # For unlimited pings some sort of break is needed to stop the ping but not halt the program.  
  # This allows a summary to display after the pings
  # This threaded function will run in the background and monitor stdin for input.
  # When the "q" key is pressed, the thread will terminate. 
  # Active status of thread can be used to determine the need to halt pings.
  def threaded_check_input(self):
    fd = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin)
    key = 0
    while key != 'q':
      key = sys.stdin.read(1)[0]
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, fd)
  
  # Function to ping an individual host.  This thread is meant to be threaded, to allow for multiple simultaneous pings.
  #     host    - the host name/address to be pinged in this thread
  #     result  - a list shared from the parent script.  This serves as a shared buffer to store ping results from threads to the main function.
  #     index   - the position within the result list where output should be stored.
  #     timeout - the timeout value to set on the ping.
  def threaded_ping(self, index):
    try:
      t = ping3.ping(self.hosts[index], timeout=self.timeout) * 1000
      self.results[index] = f"{t:.2f} ms"
      self.record_drop(index, False)
    except Exception as e:
      self.record_drop(index, True)
      if "timeout" in str(e):
        self.results[index] = f"timeout - {self.drops_active[index]}"
      elif "Unknown host" in str(e):
        self.results[index] = "unknown host"
      else:
        self.results[index] = str(e)

  # Send one ping to each host in the hosts list and capture the results
  #      hosts    - a list of hostnames/addresses to be pinged
  #      timeout  - the timeout value in seconds for each ping.
  def single_ping(self):
    threads = [None] * self.host_count
    for idx in range(self.host_count):
      threads[idx] = threading.Thread(target=self.threaded_ping, args=(idx,))
      threads[idx].start()
    sleep(self.timeout)
    while True in [thread.is_alive() for thread in threads]:
      sleep(0.01)
  
  def record_drop(self, host_idx, dropped):
    if dropped:
      self.drops_active[host_idx] += 1
      self.drops_total[host_idx] += 1
    else:
      self.drops_active[host_idx] = 0
  
  def pad_and_colorize(self):
    for idx in range(self.host_count):
      if " ms" in self.results[idx]:
        color = bcolors.GREEN
      else:
        color = bcolors.RED
      self.results[idx] = f"{color}{self.results[idx].rjust(self.__spacing)}{bcolors.ENDC}"
  
  def ping(self):
    if self.repeat == 0:
      handler = lambda x,y: print("=== press 'q' to quit ===".center((self.__spacing + 2) * self.host_count ))
      sig = signal.signal(signal.SIGINT, handler)
      thread_check = threading.Thread(target=self.threaded_check_input)
      thread_check.start()
      loop_check = lambda r: thread_check.is_alive()
    else:
      loop_check = lambda r: r < self.repeat
    ping_count = 0
    while loop_check(ping_count):
      self.single_ping()
      self.pad_and_colorize()
      print("  ".join(self.results))
      print("  ".join([host.rjust(self.__spacing) for host in self.hosts]), end="\r")
      ping_count += 1
    print("")
    print("  ".join([f"{drop} drops".rjust(self.__spacing) for drop in self.drops_total]))
    print(f"{ping_count} pings sent per host with timeout of {self.timeout}s.")
    if self.repeat == 0:
      signal.signal(signal.SIGINT, sig)


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

params = read_parameters()
mp = Multiping(hosts=params['hosts'], repeat=params['repeat'], timeout=params['timeout'])
mp.ping()



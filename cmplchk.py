#fnfgali: COMPLIANCE CHECKER
from netmiko import Netmiko
from netmiko import SSHDetect, ConnectHandler
import getpass
import pandas as pd
import time
import threading
import queue
import logging
import re
import os
import yaml
#IMPORTANT: To have a more tidy code, all check functions are created in separate files and then included here
from check_dhcp import verify_dhcp_servers_device_reg
#"comp_check" is the function where you add your compliance check function created in the imported file


logging.basicConfig(filename='app.log', filemode='w',
                    format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S',
                    level=logging.WARNING)
username = ""
username_password = ""
one_thread_semaphore = threading.BoundedSemaphore()
GLOBAL_DELAY_FACTOR = 10
DEFAULT_HOST_DICT = {"hostname": "Empty",
                     "facts": {"fqdn": None,
                              "hostname": None,
                              "vendor": None,
                              "device_type": "",
                              "model": None,
                              "serial_number": None,
                              "os_version": None,
                              "uptime": None,
                              "nw_device": False,
                              "checked": False,
                              "failed": False},
                     "lldp_neighbors"
                     "groups": []}


def read_file_list(filename):
    l = []
    with open(filename, 'r') as file:
        l = file.read().splitlines()
    return l

def get_devices_from_file(filename):
    filename = os.path.dirname(os.path.abspath(__file__))+('/'+filename)
    hostname_list = read_file_list(filename)
    return hostname_list

#--------------------------------------------------------
# FROM THIS FUNCTION YOU CALL YOUR MODULE
def comp_check(device_connect = 0):
    device_chk = {}                         # This variable stores compliance checks for a device
    option_chk = {}                         # This variable stores the output of a created module

    if device_connect != 0:
        if device_connect.device_type == 'cisco_ios':
            hostname = device_connect.base_prompt
            config = device_connect.send_command('show run')
        elif device_connect.device_type == 'juniper_junos':
            hostname = device_connect.base_prompt
            config = device_connect.send_command('show configuration | display set')
        elif device_connect.device_type == 'cisco_wlc':
            wlc_sysinfo = device_connect.send_command('show sysinfo')
            hostname = re.search(r"^(?:System Name)(?:\.+\s)([\-\w]+)\n",wlc_sysinfo,flags=re.MULTILINE).group(1)
    
    # HERE IMPLEMENT YOUR CREATED FUNCTIONS AND STORE ITS RESULT INTO "option_chk" VARIABLE
    option_chk['DHCP'] = verify_dhcp_servers_device_reg(config)

    # "device_chk" WILL STORE ALL THE CHECKS OF A SPECIFIC DEVICE
    device_chk[hostname] = option_chk
    return device_chk


def connect(hostname, myusername, mypassword):
    try:
        remote_device = {'device_type':'autodetect', 'host':hostname, 'username':myusername, 'password':mypassword}
        guesser = SSHDetect(**remote_device)
        rtr_match = str(guesser.autodetect())
    except Exception as e:
        print(e)
        return 0

    if rtr_match == 'cisco_ios':
        try:
            device_connect = ConnectHandler(host=hostname, device_type='cisco_ios', username=myusername, password=mypassword)
        except Exception as e:
            print(e)
            print("Please check and try again.")
            quit()
        return device_connect

    if rtr_match == 'cisco_wlc':
        try:
            device_connect = ConnectHandler(host=hostname, device_type='cisco_wlc', username=myusername, password=mypassword)
        except Exception as e:
            print(e)
            print("Please check and try again.")
            quit()
        return device_connect

    elif rtr_match == 'juniper_junos':
        try:
            device_connect = ConnectHandler(host=hostname, device_type='cisco_wlc', username=myusername, password=mypassword)
        except Exception as e:
            print(e)
            print("Please check and try again.")
            quit()
        return device_connect
    
    else:
        print('Router Type Not Found')
        return 0

#--------------------------------------------------------

def get_single_device_data(devices_queue, data):
    device = {
        "host": None,
        "username": username,
        "password": username_password,
        "device_type": "cisco_ios",
        "global_delay_factor": GLOBAL_DELAY_FACTOR
    }

    while not devices_queue.empty():
        try:
            # Try to get a device to work on
            # If queue is empty, don't block
            device["host"] = devices_queue.get(block=False)
            # Connect to device
            con = connect(device["host"], username, username_password)
            # Gets the device's info
            device_data = comp_check(con)
            con.disconnect()
            # Saves that info, one thread at a time
            with one_thread_semaphore:
                data.append(device_data)

            devices_queue.task_done()
            logging.info(f'{device["host"]} information retrieved.')
        except queue.Empty:
            logging.error(f'Thread tried to access the empty list.')


def get_devices_data(devices_queue, max_threads=50):
    threads = []
    data = []

    for t in range(max_threads):
        # Create all the desired threads
        t = threading.Thread(target=get_single_device_data, args=(devices_queue, data, ))
        t.start()
        threads.append(t)
    for thread in threads:
        # Wait for all the threads to continue
        thread.join()
    return data

#---------------------------------------------------------------------------------
#---------------------------------------------------------------------------------

if __name__ == '__main__':
    f = ""
    t0 = time.time()

    username = input("NVS ID: ")
    username_password = getpass.getpass()

    dlist = get_devices_from_file("hosts.ini")
    dqueue = queue.Queue()

    # Create the queue with the devices
    for device in dlist:
        dqueue.put(device)

    logging.info(f'Starting connections')
    data = get_devices_data(dqueue)
    logging.info(f'All connections ended')

    print(data)

    #Save result to .yaml
    with open('devices_compliance.yaml', mode='w') as file:
        file = yaml.dump(data, file)

    #Save result to .csv
    #df = pd.DataFrame.from_dict(data)
    #df.to_csv("devices_compliance.csv")

    logging.info(f'Data saved')
    t1 = time.time() - t0
    print("Time elapsed (secs): ", t1)  # CPU seconds elapsed (floating point)
    print("End")
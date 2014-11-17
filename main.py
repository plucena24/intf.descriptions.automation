import ssh_helper
import time
import logging
from pprint import pprint as pp
import argparse
import re


#compiled regex to strip extra data
REGEX = re.compile(r'(.*)(\(.*\))')

def ios_cdp_parser(cdp_output):

    ''' this function takes the results from
    the 'show cdp neigh detail' obtained from and IOS/IOS-XE SSH
    session and parses it. It returns a dictionary of dictionaries
    with  the interfaces as keys and the remote devices as values'''

    # start logger
    logger = logging.getLogger('__main__')
    logger.info('IOS parser starting')

    dev_info = {}

    # split the output by the newline char
    cdp_lines = cdp_output.split('\n')

    # if we see this line then reset all values
    # this line is only seen after a device has been processed

    for i in cdp_lines:
      if '-------------------------' in i:
        intf = ''
        dev_name = ''
        ip = ''
        model = ''
        remote_intf = ''
        continue

    # process the device name     
      if 'Device ID: ' in i:
        dev_name = i.split('Device ID: ')[-1].upper().strip()
        match = REGEX.search(dev_name)
        if match:
            dev_name = match.group(1)
        continue

    # process the device IP
      if (not 'ip' in locals()) or ip == '':
        if 'IP address: ' in i:
          ip = i.split('IP address: ')[-1].strip()
          continue

    # process the model - if a Nexus dev is connected, 
    # then the output will not show 'cisco'
      if 'Platform: ' in i:
        (model, junk2) = i.split(',')
        model = model.split(' ')[-1].upper()
        continue

        # if 'Platform: cisco' in i:
        #   (model, junk2) = i.split(',')
        #   model = model.split()[2].upper()
        #   continue

        # else:

        #   (model, junk2) = i.split(',')
        #   model = model.split()[1].upper()
        #   continue

            
    # process the local interface
    # build the dictionary using the local interface as the key
      if 'Interface: ' in i:
        (intf, remote_intf) = i.split(',')
        intf = intf.split()[1]

        remote_intf = format_interface_strings(remote_intf.split()[-1])
  

        dev_info[intf] = dict(Hostname=dev_name, IP_Address=ip, Model=model, Remote_Device=remote_intf)
   
    logger.info('Finished parsing the IOS CDP Data, returning the dictionary')

    # return the dictionary
    return dev_info  



def nexus_cdp_parser(cdp_output):

    ''' this function takes the results from
    the 'show cdp neigh detail' obtained from an NX-OS SSH
    session and parses it. It returns a dictionary of dictionaries
    with  the interfaces as keys and the remote devices as values'''

    # start logger
    logger = logging.getLogger('__main__')
    logger.info('Nexus Parser Starting...')

    # dev_info dict to hold data
    dev_info = {}

    # split the output by the newline char
    cdp_lines = cdp_output.split('\n')

    # if we see this line then reset all values
    # this line is only seen after a device has been processed

    for i in cdp_lines:
      if '-------------------------' in i:
        intf = ''
        dev_name = ''
        ip = ''
        model = ''
        remote_intf = ''
        continue

    # process the device name     
      if 'Device ID:' in i:
        dev_name = i.split('Device ID:')[-1].upper().strip()
        match = REGEX.search(dev_name)
        if match:
            dev_name = match.group(1)
        continue

    # process the device IP
      if (not 'ip' in locals()) or ip == '':

        if 'IPv4 Address: ' in i:
          ip = i.split('IPv4 Address: ')[-1].strip()
          continue



    # process the model - if a Nexus dev is connected, 
    # then the output will not show 'cisco'
      if 'Platform: ' in i:

          (model, junk2) = i.split(',')
          model = model.split()[1].upper()
          continue

        
    # process the local interface
    # build the dictionary using the local interface as the key
      if 'Interface: ' in i:
        (intf, remote_intf) = i.split(',')
        intf = intf.split()[1]

        remote_intf = remote_intf.split()[-1]

        remote_intf = format_interface_strings(remote_intf.split()[-1])        


        dev_info[intf] = dict(Hostname=dev_name, IP_Address=ip, Model=model, Remote_Device=remote_intf)


    
    logger.info('Finished parsing the NEXUS CDP Data, returning the dictionary') 

    # return the dictionary
    return dev_info 

    


def generate_config(device_info):

    
    ''' generate interface configuration for devices.
    This function takes a dictionary as an argument
    and returns an str of config such as: 

    'interface TenGigabitEthernet1/1/1 \n 
    description 
    '''
    logger = logging.getLogger('__main__')
    logger.info('Config Generator Starting...')

    config_list = []

    # loop through dict of dicts and generate the description config

    for intf in device_info.keys():
        interface_string = 'interface ' + intf
        config_list.append(interface_string)
        description_string = 'description %s__%s__%s__%s'% (device_info[intf]['Hostname'], device_info[intf]['Remote_Device'], device_info[intf]['Model'], device_info[intf]['IP_Address'])
        config_list.append(description_string)

  
    logger.info('Finished generating the config - returning the list')

    # return config list
    return config_list


def configure_logging(logging_file, logging_level='INFO'):

    logger = logging.getLogger('__main__')
    # logger.setLevel(getattr(logging, logging_level.upper()))
    logger.setLevel(logging_level)

    # Format for our loglines
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Setup console logging
    ch = logging.StreamHandler()
    # ch.setLevel(getattr(logging, logging_level.upper()))
    ch.setLevel(logging_level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Setup file logging as well
    fh = logging.FileHandler(logging_file)
    # fh.setLevel(getattr(logging, logging_level.upper()))
    fh.setLevel(logging_level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger


def format_interface_strings(remote_intf):

    ''' takes the str representation of the 
    remote interface for a given CDP device and
    formats it to short notation. 

    Example: GigbitEthernet = Gig
    Example: TenGigabitEthernet = Ten
    '''

    # Change from 'Ethernet' to 'Eth'

    if remote_intf.startswith('Ethernet'):

        remote_intf = remote_intf.replace('Ethernet', 'Eth')

    # Change from 'TenGigabitEthernet' to 'Ten'
    elif remote_intf.startswith('Ten'):

        remote_intf = remote_intf.replace('TenGigabitEthernet', 'Ten')

    # Change from 'GigabitEthernet' to 'Gig'
    elif remote_intf.startswith('Gig'):

        remote_intf = remote_intf.replace('GigabitEthernet', 'Gig')

    # Change from 'FastEthernet' to 'Fa'
    elif remote_intf.startswith('Fa'):

        remote_intf = remote_intf.replace('FastEthernet', 'Fa')

    return remote_intf

def main():

    DEBUG = True

    parser = argparse.ArgumentParser(description='Cisco IOS/IOS-XE and NX-OS Interface description updater script - based on current CDP data')
    parser.add_argument('--ios', help='Specify that the devices to parse are IOS devices', action='store_true', default=False)
    parser.add_argument('--nxos', help='Specify that the devices to parse are Nexus devices', action='store_true', default=False)
    parser.add_argument('--log', help='Log file location', action='store', dest='log_file', type=str, default='C:\\TEMP\\cdp_parser_log.txt')

    args = parser.parse_args()

    # extract attributes from command line args
    ios = args.ios
    nxos = args.nxos
    logfile = args.log_file


    # create logger
    logger = configure_logging(logfile)
    

    # provide creds 
    dev_creds = dict(username='XXXXXX', password='XXXXXX')

    device_list = ['vna1ds1-wan', 'vna1ds2-wan']

    for a_device in device_list:

        # instantiate ssh object
        device_obj = ssh_helper.sshHelper(host=a_device, **dev_creds)

        # connect to device 
        device_obj.connect()

        # send 'show cdp neighbor detail'
        device_obj.chan.send('show cdp neighbor detail\n')

        # wait 2 seconds for command to finish
        time.sleep(2)

        # receive buffer
        output = device_obj.read_data()

        # enter config mode
        device_obj.chan.send('configure terminal' + '\n')

        # receive buffer
        device_obj.read_data()

        # pass 'output' to cdp_parser, then pass that output
        # to generate_config. This will return a list of 
        # Cisco IOS/NX-OS syntax that can iterated over and
        # send through the SSH session to update the description
        # on each device

        # if its IOS, then call the IOS parser
        if ios:
            commands_to_send = generate_config(ios_cdp_parser(output))

        # if its Nexus, then call the Nexus parser
        elif nxos:
            commands_to_send = generate_config(nexus_cdp_parser(output))

        else:
            logger.info('Error: Need to specify IOS or Nexus device class in order to the parser to work!!! Try again with the --ios or --nxos flags.')


        logger.info('Parsing complete - about to send description commands down the SSH channel')

        # send commands from list down SSH channel

        if DEBUG:
            print
            print "*" * 80
            print
            pp(commands_to_send)
            print
            print "*" * 80

        
        if not DEBUG:

            for command in commands_to_send:
             
                # send commands down channel
                device_obj.chan.send(command + '\n')
                time.sleep(1)


        device_obj.disconnect()


if __name__ == "__main__":


    main()


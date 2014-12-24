import ssh_helper
import time
import logging
from pprint import pprint as pp
import argparse
import re
from socket import gaierror
import getpass


#CDP neighbors - hoc3ds1-dz-i.nfcu.net(JAF1724ADHG) -> to hoc3ds1-dz-i
#compiled regex to strip extra data -> remove parenthesis and domain-name.

PARENTHESIS_REGEX = re.compile(r'([a-zA-Z0-9-]*)(\..*\.NET)?(\(.*\))$')
DOMAIN_REGEX = re.compile(r'([a-zA-Z0-9-]*)(\..*\.NET)$')
INTF_SHORT = re.compile(r'((.*)?Ethernet)')


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

        # take the last item from the split line, capitalize it, stip newline, 
        # strip parenthesis or domain name.

        dev_name = strip_fields(i.split('Device ID: ')[-1].upper().strip())
        
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
            
    # process the local interface
    # build the dictionary using the local interface as the key
      if 'Interface: ' in i:
        (intf, remote_intf) = i.split(',')
        intf = intf.split()[1]

        remote_intf = format_interface_strings(remote_intf.split()[-1])

        #dev_info[intf] = dict(Hostname=dev_name, IP_Address=ip, Model=model, Remote_Device=remote_intf)
        dev_info[intf] = dict(dev_name = dev_name, ip_addr = ip, model = model, remote_intf = remote_intf)
   
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

        # take the last item from the split line, capitalize it, stip newline, 
        # strip parenthesis or domain name.

        dev_name = strip_fields(i.split('Device ID:')[-1].upper().strip())

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

        # dev_info[intf] = dict(Hostname=dev_name, IP_Address=ip, Model=model, Remote_Device=remote_intf)
        dev_info[intf] = dict(dev_name = dev_name, ip_addr = ip, model = model, remote_intf = remote_intf)
    
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


    for intf in device_info.iterkeys():

        interface_string = 'interface ' + intf

        config_list.append(interface_string)

        description_string = 'description {0[dev_name]}_{0[remote_intf]}_{0[model]}_{0[ip_addr]}'.format(device_info[intf])
       
        config_list.append(description_string)
  
    logger.info('Finished generating the config - returning the list')

    # return config list
    return config_list

    # Alternate way to generate config - this returns a generator expression
    # that can be iterated over while sending commands down the channel.

    # return ('interface {loc_int}\ndescription {dev_data[dev_name]}_{dev_data[remote_intf]}_{dev_data[model]}_{dev_data[ip_addr]}\n'.\
    #     format(loc_int=intf, dev_data=device_info[intf]) for intf in device_info.iterkeys())


def configure_logging(logging_file, logging_level='INFO'):

    logger = logging.getLogger('__main__')
    logger.setLevel(logging_level)

    # Format for our loglines
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Setup console logging
    ch = logging.StreamHandler()
    ch.setLevel(logging_level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Setup file logging as well
    fh = logging.FileHandler(logging_file)
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

    interface_mapper = dict(Ethernet='Eth', TenGigabitEthernet='Ten',
        GigabitEthernet='Gig', FastEthernet='Fa')
    
    short_name = INTF_SHORT.match(remote_intf)

    return remote_intf.replace(short_name.group(),

        interface_mapper[short_name.group()]) if short_name else remote_intf


def target_device_file(target_dev_file):

    # open file containing target devices.
    with open(target_dev_file) as f:

        #pass in a file obj containing devices separated by a '\n'
        #use a set to remove duplicates from the list, if any, and strip extra white-space.
        #return a list of target devices ready to be processed.

        devices = set([x.strip() for x in f])
        return [x for x in devices if x != '']

        # return f.read().strip().split('\n')



def strip_fields(dev_name_str):
    ''' strip the parenthesis '()' from the Nexus devices
    and the NFCU.NET from all other devices.'''
  
    if not isinstance(dev_name_str, str):
         raise ValueError('Device name is not a string...something \
            went wrong while parsing {}'.format(dev_name_str))

    parenthesis_match = PARENTHESIS_REGEX.search(dev_name_str)
    domain_name_match = DOMAIN_REGEX.search(dev_name_str)

    if parenthesis_match:
        return parenthesis_match.group(1)

    elif domain_name_match:
        return domain_name_match.group(1)

    else:
        return dev_name_str


def main():

    failed_devices = []

    DEBUG = False

    parser = argparse.ArgumentParser(description='Cisco IOS/IOS-XE and NX-OS Interface description updater script - based on current CDP data on the network.\
        Select a device type (ios or nxos) and the script will SSH into all given devices, parse CDP, and configure interface descriptions based on it.')
    parser.add_argument('-type', dest = 'type', action = 'store', choices = {'ios', 'nxos'}, help = 'Specify device type, IOS or NXOS', required = True)
    #parser.add_argument('--ios', help='Specify that the devices to parse are IOS devices', action='store_true', default=False)
    #parser.add_argument('--nxos', help='Specify that the devices to parse are Nexus devices', action='store_true', default=False)
    parser.add_argument('-l', '--log', help='Log file location', action='store', dest='log_file', type=str, default='C:\\TEMP\\cdp_parser_log.txt')
    #parser.add_argument('--log', help='Log file location', action='store', dest='log_file', type=str, default='C:\\TEMP\\cdp_parser_log.txt')
    parser.add_argument('-f', '--file', help='File with device IP or FQDN', action = 'store', dest = 'target_devices_input') 

    args = parser.parse_args()

    # extract attributes from command line args
    dev_type = args.type
    logfile = args.log_file
    target_devices_input = args.target_devices_input

    # create logger
    logger = configure_logging(logfile)
    

    # provide creds 
    dev_creds = dict(username=getpass.getuser(), password=getpass.getpass('Enter your password: '))

    if target_devices_input:
        device_list = list(target_device_file(target_devices_input))
    else:
        device_list = ['hoc3ds1-31137']
    

    for a_device in device_list:

        # instantiate ssh object
        device_obj = ssh_helper.sshHelper(host=a_device, **dev_creds)

        logger.info("Connecting to %s...", a_device)

        # connect to device
        try:
            device_obj.connect()
        except gaierror, e:
            logger.error('Failed to connect to: %s!. Continuing with the next device, if any...', a_device)
            failed_devices.append(a_device)
            continue
        
        logger.info("Collecting CDP data from %s", a_device)

        # send 'show cdp neighbor detail'
        device_obj.chan.send('show cdp neighbor detail\n')

        # wait 2 seconds for command to finish
        time.sleep(2)

        # receive buffer
        output = device_obj.read_data()

        # pass 'output' to cdp_parser, then pass that output
        # to generate_config. This will return a list of 
        # Cisco IOS/NX-OS syntax that can iterated over and
        # send through the SSH session to update the description
        # on each device

        # if its IOS, then call the IOS parser
        
        if dev_type == 'ios':
            commands_to_send = generate_config(ios_cdp_parser(output))

        # if its Nexus, then call the Nexus parser
        elif dev_type == 'nxos':
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

            logger.info("Updating interface descriptions on %s...", a_device)

            # enter config mode
            device_obj.chan.send('configure terminal' + '\n')

            # receive buffer
            device_obj.read_data()

            for command in commands_to_send:
             
                # send commands down channel and append a new-line.
                # pause for .2 seconds after each entered command.
                device_obj.chan.send(command + '\n')
                time.sleep(.20)


        logger.info("Work finished on %s. Disconecting now.", a_device)

        device_obj.disconnect()

    if failed_devices:

        print
        print "*" * 80
        print
        pp('Out of all devices given, we failed to connect to the following devices: {} . \n\
            Please verify that the FQDN or IP address being used is reachable and try again.'.format(failed_devices))
        print
        print "*" * 80
        print


if __name__ == "__main__":


    main()

import logging
import re


PARENTHESIS_REGEX = re.compile(r'([a-zA-Z0-9-]*)(\..*\.[NETCOM]+)?(\(.*\))$', re.IGNORECASE)
DOMAIN_REGEX = re.compile(r'([a-zA-Z0-9-]*)(\..*\.[NETCOM]+)$', re.IGNORECASE)
INTF_SHORT = re.compile(r'((.*)?Ethernet)')

def ios_cdp_parser(cdp_output):

    ''' this function takes the results from
    the 'show cdp neigh detail' obtained from and IOS/IOS-XE SSH
    session and parses it. It returns a dictionary of dictionaries
    with  the interfaces as keys and the remote devices as values'''

    # start logger
    logger = logging.getLogger(__name__)
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
    logger = logging.getLogger(__name__)
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
    logger = logging.getLogger(__name__)
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
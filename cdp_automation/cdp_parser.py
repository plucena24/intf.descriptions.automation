from pprint import pprint as pp


cdp_data = ''


def ios_cdp_parser(cdp_output):

    dev_info = {}

    ''' this function takes the results from
    the 'show cdp neigh detail' obtained from and IOS/IOS-XE SSH
    session and parses it. It returns a dictionary of dictionaries
    with  the interfaces as keys and the remote devices as values'''

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
        dev_name = i.split('Device ID: ')[-1].upper()
        continue

    # process the device IP
      if (not 'ip' in locals()) or ip == '':
        if 'IP address: ' in i:
          ip = i.split('IP address: ')[-1]
          continue

    # process the model - if a Nexus dev is connected, 
    # then the output will not show 'cisco'
      if 'Platform: ' in i:

        if 'Platform: cisco' in i:
          (model, junk2) = i.split(',')
          model = model.split()[2].upper()
          continue

        else:

          (model, junk2) = i.split(',')
          model = model.split()[1].upper()
          continue
        
    # process the local interface
    # build the dictionary using the local interface as the key
      if 'Interface: ' in i:
        (intf, remote_intf) = i.split(',')
        intf = intf.split()[1]
        remote_intf = remote_intf.split()[-1]
        dev_info[intf] = dict(Hostname=dev_name, IP_Address=ip, Model=model, Remote_Device=remote_intf)


    # return the dictionary
    return dev_info  



def nexus_cdp_parser(cdp_output):

    dev_info = {}

    ''' this function takes the results from
    the 'show cdp neigh detail' obtained from an NX-OS SSH
    session and parses it. It returns a dictionary of dictionaries
    with  the interfaces as keys and the remote devices as values'''

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
        dev_name = i.split('Device ID:')[-1].upper()
        continue

    # process the device IP
      if (not 'ip' in locals()) or ip == '':

        if 'IPv4 Address: ' in i:
          ip = i.split('IPv4 Address: ')[-1]
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
        dev_info[intf] = dict(Hostname=dev_name, IP_Address=ip, Model=model, Remote_Device=remote_intf)


    # return the dictionary
    return dev_info  


def generate_config(device_info):
  ''' generate interface configuration for devices.
  This function takes a dictionary of dictionaries as an argument
  and returns string of Cisco config such as: 
  'interface TenGigabitEthernet1/1/1 \n 
   description 
  '''
  for intf in device_info.keys():
    interface_string = 'interface ' + intf + '\n'
    description_string = 'description %s__%s__%s__%s'% (device_info[intf]['Hostname'],device_info[intf]['IP_Address'],device_info[intf]['Model'],device_info[intf]['Remote_Device'])
    print interface_string
    print description_string
    


generate_config(ios_cdp_parser(cdp_data))

# lines = cdp_data.split('\n')
# ip = ''
# for i in lines:
#   if 'IPv4 Address: ' in i:
#     ip = i.split('IPv4 Address: ')[-1]
#     print ip

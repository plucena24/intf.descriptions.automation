import ssh_helper
import time
import logging
from pprint import pprint as pp
import argparse
import re
from socket import gaierror
import getpass
from cdp_functions import *


#CDP neighbors - hoc3ds1-dz-i.nfcu.net(JAF1724ADHG) -> to hoc3ds1-dz-i
#compiled regex to strip extra data -> remove parenthesis and domain-name.

def configure_logging(logging_file, logging_level='INFO'):

    logger = logging.getLogger(__name__)
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


def main():

    failed_devices = []

    DEBUG = True

    parser = argparse.ArgumentParser(description='Cisco IOS/IOS-XE and NX-OS Interface description updater script - based on current CDP data on the network.\
        Select a device type (ios or nxos) and the script will SSH into all given devices, parse CDP, and configure interface descriptions based on it.')
    parser.add_argument('-type', dest = 'type', action = 'store', choices = {'ios', 'nxos'}, help = 'Specify device type, IOS or NXOS', required = True)
    parser.add_argument('-l', '--log', help='Log file location', action='store', dest='log_file', type=str, default='C:\\TEMP\\cdp_parser_log.txt')
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
        device_list = ['vna1er1-wan']
    

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
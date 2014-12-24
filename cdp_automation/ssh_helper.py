import paramiko
import time

'''
SSH Helper Module - to be used by other modules to ease
remote connection handling.
Example usage:
router1 = dict(host='1.1.1.1', username='user', password='pass')
rtr_obj = sshHelper(**router1)
rtr_obj.connect()
woo hoo
'''



class sshHelper(object):
    def __init__(self, host, username, password, port=22, delay=2):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.delay = delay

    def connect(self):
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(hostname=self.host, username=self.username, password=self.password)
            self.chan = self.ssh.invoke_shell()
            time.sleep(self.delay)
            # self.chan.recv(65535)
            self.read_data()
            self.chan.send('\n')

        except paramiko.AuthenticationException as e:
            print 'wrong username/password!', e

        self.disable_paging()

    def disconnect(self):
        self.ssh.close()

    def disable_paging(self):
        ''' disables the 'more' prompt requiring 
        a carriage return from the operator '''

        self.chan.send('terminal len 0 \n')
        self.read_data()

    def read_data(self):
        '''
        causes some delay so that the output can be read
        properly
        '''
        return self.chan.recv(65535)

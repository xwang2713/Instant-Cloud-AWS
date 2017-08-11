#---------------------------------------------------------------------------
# Copyright (C) 2011 HPCC Systems.
#
# All rights reserved. This program is free software: you can 
# redistribute it and/or modify it under the terms of the GNU 
# Affero General Public License as published by the Free Software 
# Foundation, either version 3 of the License, or (at your option) 
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#---------------------------------------------------------------------------
# Initial Author: Charles Kaminski, HPCC Systems
#                 Charles.Kaminski@LexisNexis.com
# Modifications:
# 11/26/2011 CFK Initial code created
#---------------------------------------------------------------------------
from boto.ec2.connection import EC2Connection
from boto.ec2.image import Image
from boto.ec2.instance import Instance
from boto.ec2.keypair import KeyPair
from boto.ec2 import regions, connect_to_region
from boto.ec2.securitygroup import SecurityGroup
from randcodes import readable_characters
from time import sleep

from userdata import user_data

from StringIO import StringIO
from paramiko import SSHClient, RSAKey
from paramiko import WarningPolicy, AutoAddPolicy

class Ext_SSHClient(SSHClient):
   def __init__(self):
      super(Ext_SSHClient,self).__init__()
      self.ip_address = ''
   def connect(self, ip_address, key_string):
      
      print('Connecting to %s via SSH' % ip_address)
      ssh_client = super(Ext_SSHClient,self)
      isinstance(ssh_client, SSHClient)

      self.ip_address = ip_address
      
      f = StringIO(key_string)
      paramiko_key = RSAKey.from_private_key(f)
      
      try:
         ssh_client.load_system_host_keys()
      except:
         pass
      
      ssh_client.set_missing_host_key_policy(AutoAddPolicy())
      
      tries = 0
      while True:
         try:
            ssh_client.connect(ip_address, username='ubuntu',
                               pkey=paramiko_key, timeout=1000)
            break
         except:
            tries = tries + 1
            if tries > 5:
               raise BaseException('Timed out trying to ssh to host %s'
                                   % ip_address)
            print('Waiting for SSH to %s' % ip_address)
            sleep(5)
         
      ssh_client.invoke_shell()
         
   def check_hpcc_install(self):
      # Check that the software installed properly
      print('Checking %s for installed binaries') % self.ip_address
      cmd = r"sudo tail /var/log/user-data.log"
      wait_time = 0
      while True:
         ssh_stdin, ssh_stdout, ssh_stderr = self.exec_command(cmd)
         output = ''.join(ssh_stdout.readlines()).strip()
         if output.endswith('Done'):
            break
         else:
            wait_time = wait_time + 5
            if wait_time > 600: 
               raise  BaseException("Timed out waiting for binaries to install")
            print('Waiting for binaries to install')
            sleep(5)

AMAZON_ID = '!!!! PHIL, CHANGE ME !!!!'
AMAZON_KEY = '!!!! PHIL, CHANGE ME !!!!'
REGION = 'us-east-1'
AVAILABILITY_ZONE = 'us-east-1b'
AMI_LARGE = 'ami-fbbf7892'
AMI_MICRO = 'ami-63be790a'
SIZE_LARGE = 'm1.large'
SIZE_MICRO = 't1.micro'
CLUSTER_SIZE = 10

CONFIG_FILE = '/etc/HPCCSystems/source/hpcc_config_01.xml'
ENVIRON_FILE = '/etc/HPCCSystems/environment.xml'

AMI = AMI_MICRO
AMI_SIZE = SIZE_MICRO

# Subtract 2 and round down to nearest even number
thor_nodes = (int(CLUSTER_SIZE)-2)/2*2
thor_nodes = (thor_nodes < 1) and 1 or thor_nodes

print('Connecting to AWS')
conn = connect_to_region(REGION, aws_access_key_id=AMAZON_ID, 
                         aws_secret_access_key=AMAZON_KEY)

assert(isinstance(conn, EC2Connection))

def authorize(security_group, ip_protocol = None, from_port = None, 
              to_port = None, cidr_ip = None, src_group = None):
   
   assert(isinstance(security_group,SecurityGroup))
   
   results = security_group.authorize(ip_protocol,
                                      from_port,
                                      to_port,
                                      cidr_ip,
                                      src_group)
   
   if not results: 
      raise BaseException("Security Group Auth Failed")
   

# Get Key Pairs
key_pairs = conn.get_all_key_pairs()

# Get Security Groups
security_groups = conn.get_all_security_groups()

# Generate a unique security group name
group_names    = [x.name for x in security_groups]
key_pair_names = [x.name for x in key_pairs]
while True:
   name = 'Thor-%s' % readable_characters(4)
   if (name not in group_names and 
       name not in key_pair_names): break
   
# Create new security group
print('Creating Security group %s' % name)
description = 'Visit http://hpccsystems.com for more information on Thor clusters'
new_security_group = conn.create_security_group(name, description)
assert(isinstance(new_security_group,SecurityGroup))

# Add Security Group Permission
a = new_security_group
authorize(a, 'tcp',  22,   22,    '0.0.0.0/0')
authorize(a, 'tcp',  8002, 8002,  '0.0.0.0/0')
authorize(a, 'tcp',  8008, 8008,  '0.0.0.0/0')
authorize(a, 'tcp',  8010, 8010,  '0.0.0.0/0')
authorize(a, 'tcp',  8015, 8015,  '0.0.0.0/0')
authorize(a, 'tcp',  8050, 8050,  '0.0.0.0/0')
authorize(a, 'tcp',  8145, 8145,  '0.0.0.0/0')
authorize(a, 'tcp',  9876, 9876,  '0.0.0.0/0')
authorize(a, 'tcp',  0,    65535, src_group=a)
authorize(a, 'udp',  0,    65535, src_group=a)
authorize(a, 'icmp', -1,   -1,    src_group=a)

# Create Key
print('Creating key pair %s' % name)
new_key_pair = conn.create_key_pair(name)
assert(isinstance(new_key_pair,KeyPair))

# Report new private key
f = open('temp.pem','w')
f.write(new_key_pair.material)
f.flush()

# Launch Nodes
print('Launching %s nodes' % CLUSTER_SIZE)
images = conn.get_all_images(image_ids=[AMI])
if not images: raise BaseException("AMI %s not found" % AMI)
image = images[0]
assert(isinstance(image, Image))
reservation = image.run(CLUSTER_SIZE,CLUSTER_SIZE,new_key_pair.name,
                        [new_security_group], user_data,None,AMI_SIZE)
instances = reservation.instances
      
# Wait on instances
wait_time = 0
busy_instances = [ x for x in instances]
while busy_instances:
   print('Waiting for new nodes')
   sleep(5)
   [ x.update() for x in busy_instances]
   busy_instances = [ x for x in busy_instances 
                      if x.state <> u'running']
   terminated    =  [ x for x in busy_instances
                      if x.state == u'terminated']
   if terminated:
      raise BaseException('One of the AWS nodes unexpectedly terminated')
   
   wait_time = wait_time + 5
   if wait_time > 400: 
      raise BaseException('Timed out waiting for Amazon to launch nodes.  ' + 
                          'Log into Amazon and shut down any stragglers')

#  Wait additional time for nodes to come up
#sleep(30)

# Get first node 
first_instance = instances[0]
assert(isinstance(first_instance,Instance))

# SSH to first node
ssh_client = Ext_SSHClient()
ssh_client.connect(first_instance.ip_address,
                   new_key_pair.material)

#Check that the first node's software is installed
ssh_client.check_hpcc_install()

# Create list of IP addresses
print('Creating a list of IP Addresses for cluster')
private_ips = [x.private_ip_address for x in instances]
private_ips_str = '\\;'.join(private_ips) + '\\;'
file_name = '/etc/HPCCSystems/source/ips.txt'
cmd = "sudo sh -c 'echo %s > %s'" % (private_ips_str, file_name)

# Create a file of node ip addresses
print('Creating a file with cluster ip address')
ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd)

# Checking ips.txt file
print('Checkin ips.txt file')
cmd = 'sudo cat %s' % file_name
ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd)
print(''.join(ssh_stdout.readlines()).strip())

# Run Config Manager
# ToDo: create launch config manager bash command
print('Generating the cluster environment file')
cmd = []
cmd.append('sudo /opt/HPCCSystems/sbin/envgen') 
cmd.append('-env %s' % CONFIG_FILE)
cmd.append('-ipfile /etc/HPCCSystems/source/ips.txt')
cmd.append('-roxienodes 0')
cmd.append('-thornodes %s' % thor_nodes)
cmd.append('-o log=/mnt/var/log/[NAME]/[INST]')
cmd.append('-o temp=/mnt/var/lib/[NAME]/[INST]/temp')
cmd.append('-o data=/mnt/var/lib/[NAME]/hpcc-data/[COMPONENT]')
cmd.append('-o data2=/mnt/var/lib/[NAME]/hpcc-data2/[COMPONENT]')
cmd.append('-o data3=/mnt/var/lib/[NAME]/hpcc-data3/[COMPONENT]')
cmd.append('-o mirror=/mnt/var/lib/[NAME]/hpcc-mirror/[COMPONENT]')
cmd.append('-o query=/mnt/var/lib/[NAME]/queries/[INST]')
cmd = ' '.join(cmd)
ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd)
results = ''.join(ssh_stdout.readlines()).strip()

# Read config file
print('Read the config file')
cmd = 'sudo cat %s' % CONFIG_FILE
ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd)
config = ''.join(ssh_stdout.readlines()).strip()
if not config:
   raise BaseException('Config file is empty: %s' % CONFIG_FILE)

# Prep config text for writing to terminal
config_term = config.replace('$', '\$')

# Get IP Address of ESP Server
print('Getting IP address of ESP Server')
# ProcessType,componentName,instanceip,instanceport,runtimedir,logdir
cmd = 'sudo /opt/HPCCSystems/sbin/configgen -env %s -listall' % CONFIG_FILE
ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd)
output = ssh_stdout.readlines()
line = [x.strip() for x in output 
        if x.startswith('EspProcess')]
line = line and line[0].split(',') or []
esp_private_ip = len(line)== 6 and line[2] or ''
esp_public_ip  = [x.ip_address for x in instances 
                  if x.private_ip_address == esp_private_ip]
esp_public_ip  = esp_public_ip and esp_public_ip[0] or ''

print('ESP Server IP: %s' % esp_public_ip)

"""
# Copy config file
print('Copying the cluster environment file')
cmd = []
cmd.append('sudo cp')
cmd.append('/etc/HPCCSystems/source/hpcc_config_01.xml')
cmd.append('/etc/HPCCSystems/environment.xml')
cmd = ' '.join(cmd)
ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd)

# Push config file to all nodes
print('Distributing the cluster environment file')
cmd = 'sudo -u hpcc /opt/HPCCSystems/sbin/hpcc-push.sh /etc/HPCCSystems/environment.xml /etc/HPCCSystems/environment.xml'
ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd)
"""

# Close ssh connection
print('Closing the SSH connection')
ssh_client.close()

# Bring up services
for instance in instances:
   assert(isinstance(instance, Instance))
   ssh_client = Ext_SSHClient()
   ssh_client.connect(instance.ip_address, 
                      new_key_pair.material)
   ssh_client.check_hpcc_install()

   # Set environment variables
   cmd = '/opt/HPCCSystems/sbin/hpcc_setenv'
   ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd)
   output = ''.join(ssh_stdout.readlines()).strip()
   
   # Write config file
   cmd = 'sudo tee %s << UNIQUE_EOF\n%s\nUNIQUE_EOF\n'
   cmd = cmd % (ENVIRON_FILE, config_term)
   ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd)
   output = ''.join(ssh_stdout.readlines()).strip()

   
   # Check config file
   cmd = 'sudo cat /etc/HPCCSystems/environment.xml'
   ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd)
   new_config = ''.join(ssh_stdout.readlines()).strip()
   if config.strip() == new_config.strip():
      print("New config matches original")
   else:
      print("New config DOES NOT match")
   
   # Bring up node
   print('Bringing up node %s' % ssh_client.ip_address)
   cmd = 'sudo /etc/init.d/hpcc-init start'
   ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd)
   output = ''.join(ssh_stdout.readlines()).strip()

   # Close SSH Client
   ssh_client.close()
   
   # Remove special characters from output
   output = output.replace('\x1b','')
   output = output.replace('[16m', '')
   output = output.replace('[32m', '')
   output = output.replace('[0m', '')
   
   print('Node %s' % ssh_client.ip_address)
   print(output)
   
   for line in output.splitlines():
      if not line.strip().endswith('[   OK    ]'):
         msg = []
         msg.append('Node %s services failed to start.' 
                              % ssh_client.ip_address)
         msg.append(output)
         msg = '/n'.join(msg)
         raise BaseException(msg)
   
      
print('Done')
   

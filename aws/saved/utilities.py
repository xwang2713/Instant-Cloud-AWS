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
from node_health_script import node_health_script

from random    import sample, seed
from time      import time, ctime, sleep
from StringIO  import StringIO
from os.path   import join, basename
from datetime  import datetime
from threading import Thread
from Queue     import Queue

from amara       import bindery
from paramiko    import SSHClient, RSAKey, SFTPClient
from paramiko    import WarningPolicy, AutoAddPolicy, Transport
from models      import Cluster
from django.conf import settings

import string
import logging

VERSIONS = settings.VERSIONS
SITE_ROOT = settings.SITE_ROOT
DEBUG = settings.DEBUG

READABLE_CHARACTERS = list('23456789BCDEGHJKMNPRSTUVWXYZ')
seed(time())

now = datetime.now

def is_admin(request):
    user = request.user
    is_active = user.is_active
    is_staff  = user.is_staff
    return (is_active and is_staff)

def readable_characters(length):
    return ''.join(sample(READABLE_CHARACTERS,length))

class LaunchConfig:
    def __init__(self,config_name=''):
        LAUNCH_CONFIGS = settings.AWS_LAUNCH_CONFIGS
        self.config_name = config_name
        self.config = LAUNCH_CONFIGS.itervalues().next()
        if config_name:
            self.config = LAUNCH_CONFIGS[config_name]
        self.keys = self.config.keys()
        self.keys.sort()
        self.values = [self.config[key] for key in self.keys]
    def get_key_count(self):
        return len(self.config)
    def get_sorted_keys(self):
        return self.keys
    def get_sorted_values(self):
        return self.values
    def get_value(self,idx):
        return self.values[idx]

class ClusterError(Exception):
    def __init__(self, error_message):
        self.error_message = error_message
    def __str__(self):
        return self.error_message

class NodeError(Exception):
    def __init__(self, error_message):
        self.error_message = error_message
    def __str__(self):
        return self.error_message

def write_log_entry(log_file, message):
    date_time = now().strftime("%Y/%m/%d %H:%M:%S")
    formatted_message = '%s - %s\n' % (date_time, message)
    log_file.write(formatted_message)
    log_file.flush()

def get_log_writer(cluster_id, owner_id):

    file_name = '%s-%s.txt' % (owner_id, cluster_id)
    path = join(SITE_ROOT, 'cluster_logs', file_name)

    #formatter = logging.Formatter('%(asctime)s - %(message)s')

    #handler = logging.FileHandler(path)
    #handler.setFormatter(formatter)
    #handler.setLevel(logging.INFO)

    #log = logging.getLogger('%s-%s' % (cluster_id, owner_id))
    #log.addHandler(handler)
    #log.setLevel(logging.INFO)

    log = open(path, 'a')

    return log

def get_log_entries(cluster_id, owner_id):
    file_name = '%s-%s.txt' % (owner_id, cluster_id)
    path = join(SITE_ROOT, 'cluster_logs', file_name)

    f = open(path,'r')
    log_entries = f.read()

    return log_entries

class Worker(Thread):
    """Thread executing tasks from a given tasks queue"""
    def __init__(self, tasks, logger):
        Thread.__init__(self)
        self.logger = logger
        self.tasks = tasks
        self.daemon = True
        self.start()

    def run(self):
        while True:
            func, args, kargs = self.tasks.get()
            try:
                func(*args, **kargs)
            except Exception, e:
                self.logger(str(e))
            self.tasks.task_done()

class ThreadPool:
    """Pool of threads consuming tasks from a queue"""
    def __init__(self, num_threads, logger):
        self.tasks = Queue(num_threads)
        # The logger is passed in here only for exception reporting down stream
        for _ in range(num_threads): Worker(self.tasks, logger)

    def add_task(self, func, *args, **kargs):
        """Add a task to the queue"""
        self.tasks.put((func, args, kargs))

    def wait_completion(self):
        """Wait for completion of all the tasks in the queue"""
        self.tasks.join()

class ExtSSHClient(SSHClient):
    def __init__(self, ip_address, private_ip_address, key_string, logger):
        super(ExtSSHClient,self).__init__()
        self.ip_address = ip_address
        self.private_ip_address = private_ip_address
        self.key_string = key_string.encode('ascii')
        #self.logger = lambda x: logger('%s: %s' % (ip_address, x))
        self.logger = logger

    def _raise_error(self, message):
        raise NodeError('%s: %s.' % (self.ip_address, message))

    def _run_command(self, cmd, raise_errors = True):

        if isinstance(cmd,list):
            cmd = '\n'.join(cmd)

        chan = self._transport.open_session()
        chan.exec_command(cmd)
        stdin = chan.makefile('wb', -1)
        stdout = chan.makefile('rb', -1)
        stderr = chan.makefile_stderr('rb', -1)

        stdout = stdout.readlines()
        stderr = stderr.readlines()

        stdout = ''.join(stdout)
        stderr = ''.join(stderr)

        exit_status = chan.recv_exit_status()

        if exit_status and raise_errors:
            raise ClusterError(stderr)

        return exit_status, stdout, stderr

    def mount_device(self, device, mount_point, owner=None, group=None):

        logger = self.logger

        device1 = device
        device2 = device.replace('/dev/sd', '/dev/xvd')

        # That the device exists
        cmd = 'dir /dev/'

        for i in range(24):
            exit_code, stdout, stderr = self._run_command(cmd)
            current_devices = set(stdout.split())

            if basename(device1) in current_devices:
                device = device1
                break

            if basename(device2) in current_devices:
                device = device2
                break
            logger('Waiting for EC2 instance to see storage device.')
            sleep(5)
        else:
            raise ClusterError('Timed out waiting for device.')

        # Check for a partition number
        if '%s1' % basename(device) in current_devices:
            device = '%s1' % device

        mount_point = mount_point.strip('/')
        mount_point = '%s%s%s' % ('/', mount_point, '/')

        cmd = 'sudo mkdir -p %s' % mount_point
        exit_code, stdout, stderr = self._run_command(cmd)

        cmd = 'sudo mount %s %s' % (device, mount_point)
        exit_code, stdout, stderr = self._run_command(cmd)

        if owner and group:
            cmd = 'sudo chown -R %s:%s %s' % (owner, group, mount_point)
            exit_code, stdout, stderr = self._run_command(cmd)

        logger('%s is mounted to %s.' % (device, mount_point))

    def connect(self):
        ip_address = self.ip_address
        logger = self.logger
        key_string = self.key_string

        ssh_client = super(ExtSSHClient, self)
        isinstance(ssh_client, SSHClient)

        f = StringIO(key_string)
        paramiko_key = RSAKey.from_private_key(f)

        #try:
        #    ssh_client.load_system_host_keys()
        #except:
        #    pass

        ssh_client.set_missing_host_key_policy(AutoAddPolicy())

        logger('Connecting via SSH.')
        tries = 0
        while True:
            try:
                ssh_client.connect(ip_address, username='ubuntu',
                                   pkey=paramiko_key, timeout=1000)
                break
            except:
                tries = tries + 1
                if tries > 5:
                    self._raise_error('Timed out trying to ssh to host.')

                logger('Waiting on SSH connection.')
                sleep(5)

        ssh_client.invoke_shell()

    def write_str_to_file(self, file_name, contents):
        logger = self.logger

        temp_file = '/home/ubuntu/%s' % basename(file_name)

        logger('Sending %s via SFTP.' % file_name)
        sftp = self.open_sftp()
        assert(isinstance(sftp, SFTPClient))
        new_file = sftp.file(temp_file,'w')
        new_file.write(contents)
        new_file.flush()
        sftp.close()

        if temp_file <> file_name:
            logger('Copying %s to desitnation.' % file_name)
            cmd = 'sudo cp %s %s' % (temp_file, file_name)
            exit_code, stdout, stderr = self._run_command(cmd)

        logger('Checking file contents.')
        cmd = 'sudo cat %s' % file_name
        exit_code, stdout, stderr = self._run_command(cmd)
        if stdout.strip() == contents.strip():
            logger('Remote file contents confirmed.')
        else:
            self._raise_error('File contents does not match data sent.')

    def get_config_file(self, private_ips, roxie_nodes, config_file, ips_file,
                        launch_config):

        logger = self.logger

        logger('Writing cluster private ip addresses to file on instance.')
        contents = ';'.join(private_ips) + ';'
        self.write_str_to_file(ips_file, contents)

        cluster_size = len(private_ips)

        support_nodes = 7
        size_to_support = {1: 0, 11: 1, 22: 2, 53: 3, 104: 4, 505: 5}
        for k,v in sorted(size_to_support.iteritems()):
            if cluster_size <= k:
                support_nodes = v
                break

        thor_nodes = cluster_size - support_nodes - roxie_nodes

        cmd = []
        cmd.append('sudo /opt/HPCCSystems/sbin/envgen')
        cmd.append('-env %s' % config_file)
        cmd.append('-ipfile %s' % ips_file)
        cmd.append('-roxienodes %s' % roxie_nodes)
        cmd.append('-thornodes %s' % thor_nodes)
        cmd.append('-o log=/mnt/var/log/[NAME]/[INST]')
        cmd.append('-o temp=/mnt/var/lib/[NAME]/[INST]/temp')
        cmd.append('-o data=/mnt/var/lib/[NAME]/hpcc-data/[COMPONENT]')
        cmd.append('-o data2=/mnt/var/lib/[NAME]/hpcc-data2/[COMPONENT]')
        cmd.append('-o data3=/mnt/var/lib/[NAME]/hpcc-data3/[COMPONENT]')
        cmd.append('-o mirror=/mnt/var/lib/[NAME]/hpcc-mirror/[COMPONENT]')
        cmd.append('-o query=/mnt/var/lib/[NAME]/queries/[INST]')
        cmd = ' '.join(cmd)

        logger('Running envgen')
        exit_code, stdout, stderr = self._run_command(cmd)
        results = stdout.strip()

        logger('Reading the config file.')
        cmd = 'sudo cat %s' % config_file
        exit_code, stdout, stderr = self._run_command(cmd)
        config = stdout.strip()
        if not config:
            raise self._raise_error('Config file is empty: %s' % config_file)

        # Need the ability to script the drop zone location
        config = config.replace('directory="/var/lib/HPCCSystems/dropzone"',
                                'directory="/mnt/dropzone"')

        # Need the ability to script memory settings
        large_mem_size = launch_config['hpcc_large_mem_size']
        global_memory_size = launch_config['hpcc_global_memory_size']
        mem_vals = []
        unique_identifier = 'description="Thor process"'
        mem_vals.append(unique_identifier)
        entry = '%sglobalMemorySize="%s"'
        mem_vals.append(entry % (' ' * 15, global_memory_size))
        entry = '%slargeMemSize="%s"'
        mem_vals.append(entry % (' ' * 15, large_mem_size))
        mem_vals = '\n'.join(mem_vals)
        config = config.replace(unique_identifier, mem_vals)

        # Need the ability to script enableSystemUseRewrite
        config = config.replace('enableSystemUseRewrite="false"',
                                'enableSystemUseRewrite="true"')

        # Need the ability to script roxieMulticastEnabled
        config = config.replace('roxieMulticastEnabled="true"',
                                'roxieMulticastEnabled="false"')
        return config

    def get_esp_private_ip(self, config_file):
        logger = self.logger
        logger('Retrieving IP address of ESP Server.')

        # ProcessType,componentName,instanceip,instanceport,runtimedir,logdir
        cmd = []
        cmd.append('sudo')
        cmd.append('/opt/HPCCSystems/sbin/configgen')
        cmd.append('-env %s' % config_file)
        cmd.append('-listall')
        cmd = ' '.join(cmd)
        exit_code, stdout, stderr = self._run_command(cmd)
        output = stdout.splitlines()
        line = [x.strip() for x in output
                if x.startswith('EspProcess')]
        line = line and line[0].split(',') or []
        esp_private_ip = len(line)== 6 and line[2] or ''

        if not esp_private_ip:
            self._raise_error('No ESP Server found.')

        logger('ESP Server private IP address: %s.' % esp_private_ip)

        return esp_private_ip

    def check_instance_health(self, launch_config):

        logger = self.logger
        formatting = '\n%s' % (' ' * 39)

        verbose = 1
        min_free_mem = launch_config['check_min_free_mem']
        min_free_disk = launch_config['check_min_free_disk']
        core_count = launch_config['check_core_count']

        trans = self.get_transport()
        assert(isinstance(trans, Transport))

        self.write_str_to_file('/home/ubuntu/node_health_script',
                               node_health_script)
        cmd = 'sudo chmod a+x /home/ubuntu/node_health_script'
        exit_status, stdout, stderr = self._run_command(cmd)
        if exit_status or stderr:
            raise NodeError('Could not make node_health_script executable.')

        cmd = 'sudo /home/ubuntu/./node_health_script %s %s %s %s'
        cmd = cmd % (verbose, min_free_mem, core_count, min_free_disk)
        exit_status, stdout, stderr = self._run_command(cmd)
        out = ('%s\n%s' % (stderr, stdout)).strip()

        if exit_status or stderr:
            err_msg = 'Error: Node failed health check.'
            err_msg = ('%s\n%s' % (err_msg, out)).strip()
            err_msg = err_msg.replace('\n', formatting)
            raise NodeError(err_msg)

        msg = ('No Packet, Sys logs, free ' +
               'memory, free disk, or disk I/O errors')
        logger(msg)

        #msg = []
        #msg.append('Checking EC2 instance health:')
        #msg.append('No packet issues on eth0.')
        #msg.append('No errors in system logs.')
        #msg.append(out)
        #msg = '\n'.join(msg)
        #msg = msg.replace('\n', formatting)
        #logger(msg)

        ## Info
        #memory = self._run_command('sudo cat /proc/meminfo')
        #cpu = self._run_command('sudo cat /proc/cpuinfo')
        #disk = self._run_command('sudo df -t -h')
        #network = self._run_command('sudo ifconfig')
        #mesages = self._run_command('sudo cat /var/log/messages')
        #syslog = self._run_command('sudo cat /var/log/syslog')
        #dmesg = self._run_command('sudo cat /var/log/dmesg')

    def check_hpcc_install(self, launch_config):

        logger = self.logger

        logger('Checking software installation completed.')

        # what does this return on a file that doesn't exist?
        cmd = r"sudo tail /var/log/user-data.log"

        wait_time = 0
        install_timeout = launch_config['install_timeout']
        while True:
            exit_status, stdout, stderr = self._run_command(cmd, False)
            output = stdout.strip()

            if output.endswith('Done'):
                logger('Software installation finished.')
                break
            if output.endswith('E: Some index files failed to download, they' +
                               ' have been ignored, or old ones used instead.'):
                message = ("Could not access Amazon's Ubuntu archive.  " +
                           "Try again.")
                self._raise_error(message)
            if output.endswith('No such file or directory') and wait_time > 30:
                message = ("Amazon EC2 instance failed to launch " +
                           "user-data script")
                self._raise_error(message)
            else:
                wait_time = wait_time + 10
                if wait_time > install_timeout :
                    message = 'Timed out waiting for software to install.'
                    self._raise_error(message)
                logger('Waiting for software to install.')
                sleep(10)

    def start_hpcc_services(self):
        logger = self.logger

        logger('Starting HPCC Platform Community Edition: %s.' %
               VERSIONS['hpcc'])

        cmd = 'sudo /etc/init.d/hpcc-init start'
        exit_status, stdout, stderr = self._run_command(cmd)
        output = stdout.strip()

        # Remove special characters from output
        output = output.replace('\x1b','')
        output = output.replace('[16m', '')
        output = output.replace('[32m', '')
        output = output.replace('[0m', '')

        for line in output.splitlines():
            logger(line)
            if not line.strip().endswith('[  OK  ]'):
                raise ClusterError('Service failed to start.')

def parse_landing_zone(ips_dict, cluster_config):
    """ Returns the first landing zone found.
        return (public_ip, directory)"""

    cluster_config = cluster_config.strip().encode('utf-8')

    if not ips_dict:
        raise ClusterError('Cannot parse landing zone. ' +
                           'No ip translation table. ' +
                           'Cluster may not be ready yet.')

    if not cluster_config:
        raise ClusterError('Cannot parse landing zone. ' +
                           'Config is empty. ' +
                           'Cluster may not be ready yet.')

    doc = bindery.parse(cluster_config.strip())

    # Create node to ip address translation table
    nodes = {}
    for e in doc.Environment.Hardware.Computer:
        nodes[e.name] = [e.netAddress]

    Software = doc.Environment.Software

    # attributes - build, buildSet, computer, description, directory, name
    instances = Software.DropZone
    [nodes[instance.computer].append('Drop Zone') for instance in instances]

    computer = instances[0].computer
    private_ip = nodes[computer][0]
    directory = instances[0].directory
    public_ip = ips_dict[private_ip]

    return (public_ip, directory)

def parse_node_assignments(ips_dict, cluster_config):
    """ Returns a list of [[public_ips, private_ips, processes],]"""

    cluster_config = cluster_config.strip()

    if not ips_dict:
        raise ClusterError('Cannot parse node assignments. ' +
                           'No ip translation table. ' +
                           'Cluster may not be ready yet.')

    if not cluster_config:
        raise ClusterError('Cannot parse node assignments. ' +
                           'Config is empty. ' +
                           'Cluster may not be ready yet.')

    doc = bindery.parse(cluster_config.strip().encode('utf-8'))

    # Create node to ip address translation table
    nodes = {}
    for e in doc.Environment.Hardware.Computer:
        nodes[e.name] = [e.netAddress]

    Software = doc.Environment.Software

    # attributes - computer, name
    instances = Software.ThorCluster.ThorMasterProcess
    [nodes[instance.computer].append('Thor Master') for instance in instances]

    # attributes - computer, name
    instances = Software.ThorCluster.ThorSlaveProcess
    [nodes[instance.computer].append('Thor Slave') for instance in instances]

    # attributes - computer, name
    if hasattr(Software, "RoxieCluster"):
        instances = Software.RoxieCluster.RoxieServerProcess
        for instance in instances:
            node = nodes[instance.computer]
            if node.count('Roxie Server') == 0:
                node.append('Roxie Server')

    # attributes - computer, directory, name, netAddress
    instances = Software.FTSlaveProcess.Instance
    [nodes[instance.computer].append('FT Slave') for instance in instances]

    # attributes - computer, directory, name, netAddress
    instances = Software.DafilesrvProcess.Instance
    [nodes[instance.computer].append('DA File Srvr') for instance in instances]

    # attributes - computer, directory, name, netAddress
    instances = Software.EspProcess.Instance
    [nodes[instance.computer].append('ESP') for instance in instances]

    # attributes - build, buildSet, computer, description, directory, name
    instances = Software.DropZone
    [nodes[instance.computer].append('Drop Zone') for instance in instances]

    # print 'Drop Zone', nodes[instances[0].computer][0], instances[0].directory

    # attributes - computer, directory, name, netAddress, port
    instances = Software.DaliServerProcess.Instance
    [nodes[instance.computer].append('Dali') for instance in instances]


    # attributes - computer, directory, name, netAddress
    instances = Software.DfuServerProcess.Instance
    [nodes[instance.computer].append('DFU') for instance in instances]

    # attributes - computer, directory, name, netAddress
    instances = Software.EclAgentProcess.Instance
    [nodes[instance.computer].append('ECL Agent') for instance in instances]

    # attributes - computer, directory, name, netAddress
    instances = Software.EclCCServerProcess.Instance
    [nodes[instance.computer].append('ECL CC Server') for instance in instances]

    # attributes - computer, directory, name, netAddress
    instances = Software.EclSchedulerProcess.Instance
    [nodes[instance.computer].append('ECL Scheduler') for instance in instances]

    # attributes - computer, directory, name, netAddress
    instances = Software.SashaServerProcess.Instance
    [nodes[instance.computer].append('Sasha') for instance in instances]

    # Get rid of node name
    nodes = nodes.values()
    assert(isinstance(nodes,list))

    final_nodes = []

    for node in nodes:
        private_ip = node.pop(0)
        processes = ', '.join(node)
        public_ip = ips_dict.get(private_ip, '')
        final_nodes.append([public_ip, private_ip, processes])

    # Sort by public IP address
    final_nodes.sort()

    return final_nodes
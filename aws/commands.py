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
# Source Code Modifications:
# 11/26/2011 CFK Initial code created
#---------------------------------------------------------------------------
import userdata_script
import sys
import traceback

from boto.ec2.connection import EC2Connection, Volume
from boto.ec2.image import Image
from boto.ec2.instance import Instance, Reservation
from boto.ec2.keypair import KeyPair
from boto.ec2 import regions, connect_to_region
from boto.ec2.securitygroup import SecurityGroup
from boto.exception import EC2ResponseError

from time import sleep, ctime

from django.conf import settings
from django.db import IntegrityError
from models import Cluster
from utilities import readable_characters, ClusterError, NodeError, ExtSSHClient
from cStringIO import StringIO
from paramiko import RSAKey
from utilities import ThreadPool, get_log_writer, write_log_entry
from utilities import parse_landing_zone

NAME_PREFIX = settings.AWS_CLUSTER_NAME_PREFIX
CONFIG_FILE = settings.AWS_CONFIG_FILE
ENVIRON_FILE = settings.AWS_ENVIRON_FILE
IPS_FILE = settings.AWS_IPS_FILE
POSSIBLE_DEVICES = set(['/dev/sd%s' % x for x in 'fghijklmnop'])

# EC2 Instance states: pending, running, shutting-down, terminated

def _get_running_clusters(region, access_key_id, secret_access_key):

    conn = connect_to_region(region, aws_access_key_id=access_key_id,
                         aws_secret_access_key=secret_access_key)
    assert(isinstance(conn, EC2Connection))

    # Get Key Pairs and Security Groups
    key_pairs = conn.get_all_key_pairs()
    security_groups = conn.get_all_security_groups()
    #conn.close()

    # Get Names
    group_names    = set([x.name for x in security_groups])
    key_pair_names = set([x.name for x in key_pairs])

    # Get the intersected names and filter
    isect_names = group_names & key_pair_names

    # Filter based on Thor naming convention
    cluster_names = [x for x in isect_names
                     if x.startswith(NAME_PREFIX)]

    return cluster_names

#def get_running_clusters(region, owner_id, access_key_id, secret_access_key):

    #running_clusters = _get_running_clusters(region, access_key_id,
                                             #secret_access_key)

    #clusters = Cluster.objects.filter(owner_id__exact=owner_id
                             #).filter(region__exact=region
                             #).filter(cluster_name__in=running_clusters)

    #return clusters

def get_aws_owner_id(region, access_key_id, secret_access_key):

    conn = connect_to_region(region,
                             aws_access_key_id=access_key_id,
                             aws_secret_access_key=secret_access_key)

    # Get the owner id via the security group hack
    assert(isinstance(conn, EC2Connection))
    groups = conn.get_all_security_groups()

    if groups:
        group = groups[0]
    else:
        group = conn.create_security_group('HPCCTempGroup',
                                           'HPCC Temp Group')

    # Get the owner id ... hack
    owner_id = group.owner_id

    #  If we created it, then delete it.
    if not groups:
        group.delete()

    return owner_id

def terminate_cluster(cluster_id, access_key_id, secret_access_key,
                      owner_id, delete_ebs_volumes):

    cluster = Cluster.objects.get(pk=cluster_id, owner_id = owner_id)

    region = cluster.region
    cluster_name = cluster.cluster_name

    #logger = lambda x: add_new_log_entry(cluster_id, x)
    log = get_log_writer(cluster_id, owner_id)
    logger = lambda x: write_log_entry(log, x)
    logger('Terminating cluster.')

    if not cluster_name:
        logger('Cluster has no name.  Marking cluster record as terminated.')
        logger('Confirm the appropriate instances are terminated in your ' +
               'Amazon Management Console ')
        cluster.is_terminated = True
        cluster.save()
        logger('Done.')
        return

    if not region:
        logger('Error: The region of the cluster is not found.')
        logger('Log into your AWS Management Console and delete the' +
               'appropriate instances')
        cluster.is_terminated = True
        cluster.save()
        return

    logger('Connecting to AWS region %s.' % region)

    try:
        conn = connect_to_region(region, aws_access_key_id=access_key_id,
                                 aws_secret_access_key=secret_access_key)
        assert(isinstance(conn, EC2Connection))

        logger('Gathering instances for %s.' % cluster_name)
        if (region == 'eu-central-1'):
            filters = {'key-name':cluster_name}
        else:
            filters = {'key-name':cluster_name, 'group-name':cluster_name}
        reservations = conn.get_all_instances(filters=filters)

        instances = []
        for reservation in reservations:
            instances.extend(reservation.instances)

        _terminate_instances(instances, delete_ebs_volumes, logger)

        logger('Deleting Access Key %s.' % cluster_name)
        try:
            key_pairs = conn.get_all_key_pairs(keynames=[cluster_name])
            [x.delete() for x in key_pairs]
        except EC2ResponseError, e:
            if e.error_code == u'InvalidKeyPair.NotFound':
                logger('Error: Access key not found.')
            else:
                raise

        logger('Deleting Security group %s.' % cluster_name)
        try:
            security_groups = conn.get_all_security_groups(groupnames=
                                                           [cluster_name])
            [x.delete() for x in security_groups]
        except EC2ResponseError, e:
            if e.error_code == u'InvalidGroup.NotFound':
                logger('Error: Security group not found.')
            else:
                raise

    except Exception, e:
        _log_exception(logger, e)
        cluster.is_terminate_failed = True
        cluster.save()
        raise

    cluster.is_terminated = True
    cluster.save()

    logger('Done.')


def launch_cluster(node_count, roxie_nodes, cluster_id, launch_config,
                   access_key_id, secret_access_key, owner_id):

    region = launch_config['region']

    cluster = Cluster.objects.get(pk=cluster_id)
    cluster.is_launching = True
    cluster.save()

    log = get_log_writer(cluster_id, owner_id)
    logger = lambda x: write_log_entry(log, x)
    #logger = lambda x: add_new_log_entry(cluster_id, x)

    try:
        logger('Connecting to AWS region %s.' % region)
        conn = connect_to_region(region, aws_access_key_id=access_key_id,
                                 aws_secret_access_key=secret_access_key)

        storage_ids = launch_config.get('ebs_storage_ids', '')
        storage_ids = storage_ids.replace(',',' ').replace(';',' ')
        storage_ids = storage_ids.split()

        volumes = [x for x in storage_ids if x.startswith('vol')]
        if volumes:
            message = 'To discourage data loss, we currently only attach ' + \
                      'EBS volumes from snapshots: %s'
            message = message % ','.join(volumes)
            raise ClusterError(message)

        volumes, snapshots = [], []
        if storage_ids:
            message = 'Checking storage IDs exist in region %s: %s'
            message = message % (region, ', '.join(storage_ids))
            logger(message)
            vs = _get_volumes_snapshots(storage_ids, conn, logger)
            volumes, snapshots = vs

        message = 'Calculating new unique cluster name for request %s.'
        logger(message % cluster_id)
        cluster_name = _calculate_cluster_name(conn, cluster, logger)

        logger('Creating %s security group.' % cluster_name)
        security_group = _create_security_group(conn, cluster_name)

        logger('Creating %s key pair.' % cluster_name)
        key_pair = conn.create_key_pair(cluster_name)
        cluster.ssh_key = key_pair.material
        cluster.save()
       
        user_data = launch_config['user_data_script']
        user_data = _insert_rsa_keys(user_data,
                                     key_pair.material, cluster_name)
        
        instances = _launch_nodes(conn, node_count, key_pair, security_group,
                                  launch_config, user_data, logger)

        logger('Determining availability zone.')
        instance = instances[0]
        assert(isinstance(instance, Instance))
        availability_zone = instance.placement
        cluster.availability_zone = availability_zone
        cluster.save()

        logger('Gathering public and private ip addresses.')
        private_ips = [x.private_ip_address for x in instances]
        public_ips = [x.ip_address for x in instances]
        public_ip_lookup = dict(zip(private_ips, public_ips))

        cluster.private_ips = '\n\\;'.join(private_ips) + '\\;'
        cluster.public_ips = '\n\\;'.join(public_ips) + '\\;'
        cluster.save()

        # Get first instance for future use
        first_instance = instances[0]

        # SSH to first node.  Messages go to logger
        message = 'Connecting to node %s for cluster configuration.'
        logger(message % first_instance.ip_address)
        ssh_client =  ExtSSHClient(first_instance.ip_address,
                                   first_instance.private_ip_address,
                                   key_pair.material, logger)

        ssh_client.connect()
        ssh_client.check_hpcc_install(launch_config)
        ssh_client.check_instance_health(launch_config)
        large_mem_size = launch_config['hpcc_large_mem_size']
        global_memory_size = launch_config['hpcc_global_memory_size']
        cluster_config = ssh_client.get_config_file(private_ips, roxie_nodes,
                                                    CONFIG_FILE, IPS_FILE, 
                                                    launch_config)

        # Save cluster config in database for future reference
        cluster.configuration = cluster_config
        cluster.save()

        # Get public esp address
        esp_private_ip = ssh_client.get_esp_private_ip(CONFIG_FILE)
        esp_public_ip = public_ip_lookup.get(esp_private_ip)
        logger('ESP Server public IP address: %s.' % esp_public_ip)
        cluster.esp = esp_public_ip
        cluster.save()

        ssh_client.close()

        # Attach EBS Storage
        landing_zone = parse_landing_zone(public_ip_lookup, cluster_config, logger)
        landing_zone_ip, landing_zone_path = landing_zone
        if volumes or snapshots:
            message = 'Attaching storage devices to the Landing Zone: %s'
            ids = [x.id for x in (volumes + snapshots)]
            message = message % ', '.join(ids)
            logger(message)
            try:
                _attach_ebs_devices(landing_zone_ip, landing_zone_path, volumes,
                                    snapshots, key_pair.material, conn, logger)
            except Exception, e:
                _log_exception(logger, e)

        _start_cluster_services(public_ips, private_ips, key_pair.material,
                                ENVIRON_FILE, cluster_config, cluster_id,
                                launch_config, logger)

        cluster.is_launched = True
        cluster.save()
        logger('Done.')

    except Exception, e:
        _log_exception(logger, e)
        cluster.is_launch_failed = True
        cluster.save()
        raise

def _get_volumes_snapshots(storage_ids, conn, logger):
    """Get volumes and snapshots for a given region.  Check that the volumes
       are available.

       Returns -> (volumes, snapshots)"""

    region = conn.region
    assert(isinstance(conn, EC2Connection))

    volume_ids   = [x for x in storage_ids if x.startswith('vol')]
    snapshot_ids = [x for x in storage_ids if x.startswith('snap')]
    invalid_ids  = [x for x in storage_ids if not x.startswith('snap') and
                                              not x.startswith('vol')]

    if invalid_ids:
        message = 'Invalid volume IDs or snapshot IDs: %s.'
        message = message % ', '.join(invalid_ids)
        raise ClusterError(message)

    volumes, snapshots = [], []

    if volume_ids:
        volumes = conn.get_all_volumes(volume_ids)
    if snapshot_ids:
        snapshots = conn.get_all_snapshots(snapshot_ids)

    for volume in volumes:
        status = volume.update()
        if status <> u'available':
            message = 'Volume is not available: %s - %s' % (volume.id, status)
            raise ClusterError(message)

    return (volumes, snapshots)

def _attach_ebs_devices(landing_zone_ip, landing_zone_path, volumes, snapshots,
                        ssh_key, conn, logger):

    volumes = list(set(volumes))
    volumes.sort()
    snapshots = list(set(snapshots))
    snapshots.sort()

    assert(isinstance(conn, EC2Connection))

    # Find landing zone instance
    filters = {'ip-address':landing_zone_ip}
    reservations = conn.get_all_instances(filters=filters)
    try:
        instance = reservations[0].instances[0]
        assert(isinstance(instance, Instance))
    except:
        message = 'Error - Could not find Landing Zone EC2 instance ' + \
                  'with ip address %s.'
        message = message % landing_zone_ip
        raise ClusterError(message)

    # Check volumes and get list of existing connected instances.
    filters = {'attachment.instance-id':instance.id}
    volumes = conn.get_all_volumes(filters=filters)
    devices_used = set([x.attach_data.device for x in volumes])
    snapshots_used = set([x.snapshot_id for x in volumes])
    volumeids_used = set([x.id for x in volumes])

    for i, snapshot in enumerate(snapshots[:]):
        if snapshot.id in snapshots_used:
            message = 'The snapshot %s is already attached to the cluster.'
            message = message % snapshot.id
            logger(message)
            snapshots.pop(i)

    for i, volume in enumerate(volumes[:]):
        if volume.id in volumeids_used:
            message = 'The volume %s is already attached to the cluster.'
            message = message % volume.id
            loggger(message)
            volumes.pop(i)

    available_devices = list(POSSIBLE_DEVICES - devices_used)
    available_devices.sort()
    if not available_devices:
        message = 'Error - EC2 Instances are limited to 11 additional devices.'
        raise ClusterError(message)

    # Turn snapshots into volumes
    snapshot_volumes = []
    for snapshot in snapshots:
        volume = conn.create_volume(0, instance.placement, snapshot.id)
        snapshot_volumes.append(volume)

    # wait for volumes to become available
    message = 'Waiting for volumes to become available.'
    wait_list = snapshot_volumes + volumes
    for i in range(24):
        [x.update() for x in wait_list]
        wait_list = [x for x in wait_list if x.status <> u'available']
        if wait_list:
            logger(message)
            sleep(5)
        else:
            break
    else:
        message = 'Error - Timed out waiting for EBS volumes: %'
        message = message % ', '.join(wait_list)
        raise ClusterError(message)

    # Attache Volumes to instance
    attach_list = snapshot_volumes + volumes
    joined_list = zip(available_devices, attach_list)
    for device, volume in joined_list:
        volume.attach(instance.id, device)

    # wait for volumes to Attach
    message = 'Waiting for volumes to attach to landing zone.'
    wait_list = snapshot_volumes + volumes
    for i in range(24):
        [x.update() for x in wait_list]
        wait_list = [x for x in wait_list if x.status <> u'in-use']
        if wait_list:
            logger(message)
            sleep(5)
        else:
            break
    else:
        message = 'Error - Timed out waiting for EBS volumes to attach: %'
        message = message % ', '.join(wait_list)
        raise ClusterError(message)


    # Mount EBS devices to landing zone
    ssh_client = ExtSSHClient(instance.ip_address, instance.private_ip_address,
                              ssh_key, logger)
    ssh_client.connect()
    for volume in snapshot_volumes:
        mount_point = '%s/%s' % (landing_zone_path, volume.snapshot_id)
        device = volume.attach_data.device
        ssh_client.mount_device(device, mount_point, 'hpcc', 'hpcc')

    for volume in volumes:
        mount_point = '%s/%s' % (landing_zone_path, volume.id)
        device = volume.attach_data.device
        ssh_client.mount_device(device, mount_point, 'hpcc', 'hpcc')

    ssh_client.close()


def _launch_nodes(conn, node_count, key_pair, security_group,
                  launch_config, user_data, logger):

    instance_size = launch_config['instance_size']
    ami = launch_config['ami']

    message = 'Launching %s %s nodes using %s.' % (node_count, instance_size,
                                                   ami)
    logger(message)

    # Find AMI Image
    assert(isinstance(conn, EC2Connection))
    images = conn.get_all_images(image_ids=[ami])

    if not images: raise ClusterError("AMI %s not found on AWS." % ami)
    image = images[0]
    assert(isinstance(image,Image))

    availability_zone = None
    bad_instances = []
    good_instances = []

    # Try 4 times to get a good set of nodes
    for x in range(4):

        nodes_needed = node_count - len(good_instances)

        # Launch Nodes
        if nodes_needed != node_count:
            logger('Launching %s new nodes.' % nodes_needed)
        reservation = image.run(nodes_needed,nodes_needed,key_pair.name,
                                [security_group], user_data, None,
                                instance_size, availability_zone)
        assert(isinstance(reservation, Reservation))

        logger('Reservation ID %s created.' % reservation.id)
        instances = reservation.instances

        # Wait for nodes to launch
        _wait_for_new_nodes(instances, nodes_needed, logger)

        # Get avialability_zone
        if not availability_zone:
            instance = instances[0]
            assert(isinstance(instance, Instance))
            availability_zone = instance.placement

        # Mark bad instances
        _mark_bad_instances(instances, key_pair, launch_config, logger)

        # Separate good instances and bad instances
        bad_instances = [x for x in instances if x.bad_instance]
        instances     = [x for x in instances if not x.bad_instance]

        good_instances.extend(instances)

        if bad_instances:
            message = 'Terminating %s bad instances.'
            logger(message % len(bad_instances))
            _terminate_instances(bad_instances, True, logger)
        else:
            break
    else:
        raise ClusterError('Failed to launch the nodes requested.')

    return good_instances


def _mark_bad_instances(instances, key_pair, launch_config, logger):

    logger('Checking each node launched properly.')

    debug = False

    if debug:
        for instance in instances:
            _mark_bad_instance(instance, key_pair, launch_config, logger)
    else:
        queue_size = len(instances) > 25 and 25 or len(instances)
        thread_pool = ThreadPool(queue_size, logger)

        for instance in instances:
            thread_pool.add_task(_mark_bad_instance,
                                 instance, key_pair, launch_config, logger)

        thread_pool.wait_completion()

def _mark_bad_instance(instance, key_pair, launch_config, logger):
        assert(isinstance(instance, Instance))

        ip_address = instance.ip_address
        private_ip_address = instance.private_ip_address
        material = key_pair.material

        padded_ip = ('%s: ' % ip_address).ljust(17)
        logger_ip = lambda x: logger('%s%s' % (padded_ip, x))

        logger_ip('Checking EC2 instance %s.' % instance.id)

        ssh_client = ExtSSHClient(ip_address, private_ip_address,
                                  material, logger_ip)

        try:
            instance.update()
            logger_ip('Checking EC2 instance is running.')
            if instance.state <> u'running':
                message = 'Node %s failed to launch properly.' % ip_address
                raise NodeError(message)

            ssh_client.connect()
            ssh_client.check_hpcc_install(launch_config)
            ssh_client.check_instance_health(launch_config)
            ssh_client.close()
            instance.bad_instance = False
        except NodeError, e:
            logger_ip(e.error_message)
            logger_ip('Error - Node %s failed check.' % ip_address)
            instance.bad_instance = True
        except Exception, e:
            logger('Unhandled error occured when checking for bad instances')
            _log_exception(logger, e)
            instance.bad_instance = True
            raise
        finally:
            logger_ip('Completed check of node %s.' % ip_address)

def _terminate_instances(instances, delete_ebs_volumes, logger):
    logger('Terminating instances.')

    volumes = []

    terminating_instances = []
    for instance in instances:
        assert(isinstance(instance, Instance))

        devices = instance.block_device_mapping.values()
        volume_ids = [x.volume_id for x in devices]
        if volume_ids:
            new_volumes = instance.connection.get_all_volumes(volume_ids)
            volumes.extend(new_volumes)

        instance.terminate()
        terminating_instances.append(instance)

    for count in range(72):
        # 72 * 5 seconds = 6 minutes
        [x.update() for x in terminating_instances]
        terminating_instances = [x for x in terminating_instances if
                                 x.state <> u'terminated']

        if not terminating_instances:
            break
        logger('Waiting for %s instances to terminate.' %
                                 len(terminating_instances))
        sleep(5)
    else:
        raise NodeError('Timed out waiting for instances to terminate.')

    if volumes and delete_ebs_volumes:
        logger('Deleting attached EBS volumes.')
        for volume in volumes:
            logger('Deleting volume %s' % volume.id)
            try:
                volume.delete()
            except Exception, e:
                logger('Volume %s failed to delete.' % volume.id)
                _log_exception(logger, e)

def _wait_for_new_nodes(instances, node_count, logger):

    message_template = 'Waiting for %s of %s nodes to launch.'
    pending_instances = [ x for x in instances]

    for count in range(120):
        # 120 * 5 seconds = 600 seconds = 10 minutes
        message = message_template % (len(pending_instances), node_count)
        logger(message)
        sleep(5)

        tries = 3
        while True:
            try:
                [x.update() for x in pending_instances]
            except EC2ResponseError, e:
                _log_exception(logger, e)
                tries = tries - 1
                if tries:
                    logger('Error occured when trying to update status.')
                    logger('Pausing 10 seconds before trying again.')
                    sleep(10)
                else:
                    raise
            else:
                break

        pending_instances = [ x for x in pending_instances
                                   if x.state == u'pending']

        if not pending_instances:
            logger('Pending instances have completed.')
            break

        # State is double checked in _mark_bad_instances
        # Any instances that have not come up will be marked bad and terminated

    # Amazon nodes are not coming up properly..See note above
    #else:
    #    raise ClusterError('Timed out waiting for Amazon to launch nodes.')
    #
    #running_instances = [x.state for x in instances if x.state == u'running']

    #if len(running_instances) <> node_count:
    #    states = [ x.state for x in instances ]
    #    raise ClusterError('Not all the instances came up: \n%s' %
    #                         '\n'.join(states))



def _insert_rsa_keys(user_data, private_key, cluster_name):

    private_key = private_key.encode('ascii')

    f = StringIO(private_key)
    key_obj = RSAKey.from_private_key(f)

    public_key = "'%s %s %s'" % (key_obj.get_name(), key_obj.get_base64(),
                                 cluster_name)

    private_key = "'%s'" % private_key

    user_data = user_data.replace("'RSAPRIVATEKEY'", private_key)
    user_data = user_data.replace("'RSAPUBLICKEY'", public_key)

    return user_data

def _authorize(security_group, ip_protocol = None, from_port = None,
              to_port = None, cidr_ip = None, src_group = None):

    assert(isinstance(security_group,SecurityGroup))

    results = security_group.authorize(ip_protocol, from_port, to_port,
                                       cidr_ip, src_group)

    if not results:
        raise ClusterError("Security Group Authorization Failed")

def _create_security_group(conn, cluster_name):

    description = ('Visit http://hpccsystems.com for ' +
                   'more information on HPCC clusters')
    security_group = conn.create_security_group(cluster_name, description)
    assert(isinstance(security_group,SecurityGroup))

    # Add Security Group Permission
    a = security_group
    _authorize(a, 'tcp',  22,   22,    '0.0.0.0/0')
    _authorize(a, 'tcp',  8002, 8002,  '0.0.0.0/0')
    _authorize(a, 'tcp',  8008, 8008,  '0.0.0.0/0')
    _authorize(a, 'tcp',  8010, 8010,  '0.0.0.0/0')
    _authorize(a, 'tcp',  8015, 8015,  '0.0.0.0/0')
    _authorize(a, 'tcp',  8050, 8050,  '0.0.0.0/0')
    _authorize(a, 'tcp',  8145, 8145,  '0.0.0.0/0')
    _authorize(a, 'tcp',  9876, 9876,  '0.0.0.0/0')
    _authorize(a, 'tcp',  0,    65535, src_group=a)
    _authorize(a, 'udp',  0,    65535, src_group=a)
    _authorize(a, 'icmp', -1,   -1,    src_group=a)

    return security_group

def _calculate_cluster_name(conn, cluster, logger):
    # find key pair and security group names
    key_pairs = conn.get_all_key_pairs()
    security_groups = conn.get_all_security_groups()
    key_pair_names = set([x.name for x in key_pairs])
    group_names    = set([x.name for x in security_groups])
    cluster_names = group_names | key_pair_names

    for x in range(20):

        chars = (x/5) + 4
        cluster_name = NAME_PREFIX + readable_characters(chars)

        if cluster_name in cluster_names:
            continue
        try:
            cluster.cluster_name = cluster_name
            cluster.save()
            logger('Creating new cluster name, %s.' % cluster_name)
            break
        except IntegrityError:
            #logger('Cluster name %s already exists.  Recalculating.' %
            #       cluster_name)
            continue
    else:
        raise ClusterError('Failed to calculate a unique cluster name.')

    return cluster_name

def _start_cluster_services(ip_addresses, private_ips, key_string,
                            config_path, config_string, cluster_id,
                            launch_config, logger):

    debug = False

    ips = zip(ip_addresses, private_ips)

    if debug:
        for ip_address, private_ip in ips:
            _start_node_services(logger, cluster_id, ip_address, private_ip,
                                 key_string, config_path, config_string,
                                 launch_config)

    else:
        queue_size = len(ip_addresses) > 25 and 25 or len(ip_addresses)
        thread_pool = ThreadPool(queue_size, logger)

        for ip_address, private_ip in ips:
            thread_pool.add_task(_start_node_services,
                                 logger, cluster_id, ip_address, private_ip,
                                 key_string, config_path, config_string,
                                 launch_config)

        thread_pool.wait_completion()

    # May want to put a check here later -
    # Did all of the instances report back?

def _start_node_services(logger, cluster_id, ip_address, private_ip_address,
                         key_string, config_path, config_string, launch_config):
    #logger = [].append
    padded_ip = ('%s: ' % ip_address).ljust(17)
    logger_ip = lambda x: logger('%s%s' % (padded_ip, x))
    #logger_ip = logger

    cluster = Cluster.objects.get(pk=cluster_id)
    is_failed = cluster.is_launch_failed

    logger_ip('Starting node configuration.')

    try:
        if is_failed:
            logger_ip('Prior node failure detected. Skipping node.')
        else:
            ssh_client =  ExtSSHClient(ip_address, private_ip_address,
                                       key_string, logger_ip)
            ssh_client.connect()
            ssh_client.check_hpcc_install(launch_config)
            ssh_client.check_instance_health(launch_config)
            ssh_client.write_str_to_file(config_path, config_string)
            ssh_client.start_hpcc_services()
            ssh_client.close()
    except Exception, e:
        cluster.is_launch_failed = True
        cluster.save()
        _log_exception(logger, e)
        raise
    finally:
        logger_ip('Start node is complete.')

def _log_exception(logger, e):
    message = []
    message.append('An exception occured.')
    #message.append('Writing traceback to internal error log.')
    #message.append('Please contact us at info@hpccsystems.com for assistance.')
    #message.append('Include in the email the cluster ID')
    #message.append('or the URL for this page.')

    exc_type, exc_value, exc_traceback = sys.exc_info()

    if isinstance(e, EC2ResponseError):
        tb = []
        tb.append('Amazon Error: %s' % e.error_code)
        tb.append(e.error_message)
        tb.append('requestId: %s' % e.request_id)
    else:
        tb = traceback.format_exception_only(exc_type, exc_value)

    tb = [x.strip() for x in tb]
    message.extend(tb)

    formatting = '\n%s' % (' ' * 22)

    message = formatting.join(message)
    logger(message)

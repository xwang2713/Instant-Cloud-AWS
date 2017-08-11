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
# 12/27/2011 CFK Modifed code
#---------------------------------------------------------------------------
user_data = r"""#!/bin/bash -ex
#---------------------------------------------------------------------------
# Initial configuration and installation script to run HPCC on Amazon's
# EC2 environment.  This script is to be passed into the User Data field
# and is run when the EC2 instance boots.
# Author:        Charles Kaminski, HPCC Systems
#                charles.kaminski@lexisnexis.com
# Date:          06/08/2011
# Arguments:     None
# Source Code Modifications:
# 08/22/2011  Changed owner ship of /mnt/ to user hpcc
# 09/16/2011  Added install expect
# 09/16/2011  Added command to change ownership of environment file
# 09/26/2011  Updated platform version
# 10/17/2011  Updated platform version
# 11/19/2011  Added Paramiko and boto to automate large cluster config
# 11/29/2011  Updated platform version
# 12/09/2011  Added commands to create /var/lib/HPCCSystems and
#                                      /var/log/HPCCSystems
# 01/30/2012  Updated platform version
#---------------------------------------------------------------------------
## = = R E A D  M E  = = R E A D  M E  = = R E A D  M E  = =
## The below keys enable the HPCC's nodes to communicate to each other
## through the account "hpcc".  Replace the below keys with your own
## private and public keys.  Because the below Amazon startup script is
## accessible to anyone you grant system command-line access to, you
## should not use long-lived keys or keys you use for other purposes.
## For additional security, you can log into each node directly and change
## the access keys for user "hpcc".  See /home/hpcc/.ssh/
##
## Output for debugging this script is written to /var/log/user-data.log


# Set certain variables
CLIENTTOOLS=hpccsystems-clienttools-community_3.4.2-1-noarch.deb
DOCUMENTATION=hpccsystems-documentation-community_3.4.2-1-noarch.deb
GRAPHCONTROL=hpccsystems-graphcontrol-community_3.4.2-1-noarch.deb
PLATFORM=hpccsystems-platform_community-3.4.2-1lucid_amd64.deb
IPSAPP=ips

# Bucket is replaced by settings in settings.py
IFLOCATION=http://S3_BUCKET.s3.amazonaws.com/communityedition/03.4.2-1/

RSAPRIVATEKEY='RSAPRIVATEKEY'

RSAPUBLICKEY='RSAPUBLICKEY'

# Setting up user hpcc
groupadd hpcc-test
useradd -G hpcc-test hpcc

mkdir /home/hpcc
mkdir /home/hpcc/.ssh

echo -e ${RSAPRIVATEKEY//[[:cntrl:]]/'\n'} >> /home/hpcc/.ssh/id_rsa
echo $RSAPUBLICKEY >> /home/hpcc/.ssh/authorized_keys

chown -R hpcc:hpcc-test /home/hpcc
chmod 600 /home/hpcc/.ssh/authorized_keys
chmod 600 /home/hpcc/.ssh/id_rsa

# Turning on logging
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo 'User hpcc has been setup'

install()
{
    DEBIAN_FRONTEND=noninteractive apt-get -y \
        -o DPkg::Options::=--force-confdef \
        -o DPkg::Options::=--force-confold \
        install $@
}

echo 'Installing HPCC dependancies'
apt-get update
install libicu42
install libxalan110
install libxerces-c28
install openssl
install binutils
install g++
install build-essential
install libboost-regex1.40.0

install libicu-dev
install libboost1.40-dev

install libboost-regex1.40-dev
install libboost-regex-dev
install libldap-2.4-2
install libldap2-dev

install expect
install tofrodos

echo 'Installing automation support for large cluster config'
install python-paramiko
install python-boto

echo 'Changing working directory to /home/ubuntu'
cd /home/ubuntu

echo 'Downloading the HPCC install files'
wget --progress=dot:mega --tries 5 $IFLOCATION$PLATFORM
wget --progress=dot:mega --tries 5 $IFLOCATION$CLIENTTOOLS
wget --progress=dot:mega --tries 5 $IFLOCATION$DOCUMENTATION
wget --progress=dot:mega --tries 5 $IFLOCATION$GRAPHCONTROL

chown -R ubuntu:ubuntu /home/ubuntu/

echo 'Installing HPCC binaries'
dpkg -i $PLATFORM
dpkg -i $CLIENTTOOLS
dpkg -i $DOCUMENTATION
dpkg -i $GRAPHCONTROL

echo 'Install HPCC AWS helper files'
cd /opt/HPCCSystems/sbin/
wget --progress=dot:mega --tries 5 $IFLOCATION$IPSAPP
fromdos $IPSAPP
chmod +x $IPSAPP

##echo 'Adding Multiverse'
##cat >>/etc/apt/sources.list <<EOF
##deb http://us.archive.ubuntu.com/ubuntu/ hardy multiverse
##deb-src http://us.archive.ubuntu.com/ubuntu/ hardy multiverse
##deb http://us.archive.ubuntu.com/ubuntu/ hardy-updates multiverse
##deb-src http://us.archive.ubuntu.com/ubuntu/ hardy-updates multiverse
##EOF
##apt-get update
##
##echo 'Adding EC2 API tools'
##install ec2-api-tools

echo 'Changing ownership of /mnt to hpcc user'
chown -R hpcc:hpcc /mnt/

echo 'Changing ownership HPCC directories'
chown hpcc:hpcc -R /etc/HPCCSystems
chown hpcc:hpcc -R /opt/HPCCSystems

mkdir -p /var/lib/HPCCSystems
mkdir -p /var/log/HPCCSystems
chown -R hpcc:hpcc /var/lib/HPCCSystems
chown -R hpcc:hpcc /var/log/HPCCSystems

echo 'Done'
"""

if __name__ == '__main__':
    pass
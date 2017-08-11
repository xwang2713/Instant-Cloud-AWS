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
# 02/07/2012 CFK Added script from Jon Burger's team
# 03/01/2012 CFK Omit landingzone storage devices
#---------------------------------------------------------------------------
node_health_script="""#!/bin/bash
# Error Check for system resources / error conditions

EXPECTED_ARGS=4

if [ $# -ne $EXPECTED_ARGS ]; then
	echo "USAGE: <verbose> <min free memory(kb)> <cpu cores> <free disk storage>"
	exit 1
fi

# Script behavior variables
VERBOSE=$1
ERRORS=0

# MINIMUM THREHOLDS to indicate error:
MEM_FREE_MIN=$2
CORE_COUNT_MIN=$3
DISK_FREE_MIN=$4

# Helper functions
log_err () {
	echo $@ >&2
}

log_msg () {
	[ ${VERBOSE:-0} -eq 1 ] && echo $@
}

if [ ${UID:?UID not set} -ne 0 ]; then
	echo "Script not running as root" >&2
	exit 1
fi

##############################################################
# Start of gathering metrics
##############################################################ns

# Free Memory
MEM_FREE=$(awk '/^MemFree:/ { print $2 }' < /proc/meminfo)
if [ ${MEM_FREE} -lt ${MEM_FREE_MIN:-2048000} ]; then
	ERRORS=$(($ERRORS+1))
	log_err "Free memory: ${MEM_FREE} kB Less than minimum ${MEM_FREE_MIN:-2048000}"
else
	log_msg "Free memory: ${MEM_FREE} kB"
fi

# CPU Info
IFS=$'\n'
declare -a CPU_INFO=( $(awk -F: '/^processor/ { CPU_NUM=$2 } /^model name/ { CPU_NAME=$2 } /^core id/ { print CPU_NUM":"$2 " - " CPU_NAME}' < /proc/cpuinfo) )
CORE_COUNT=${#CPU_INFO[@]}

if [ ${CORE_COUNT} -lt ${CORE_COUNT_MIN:-4} ]; then
	ERRORS=$(($ERRORS+1))
	log_err "Core count ${CORE_COUNT} Less than minimum ${CORE_COUNT_MIN:-4}"
else
	for CPU in ${CPU_INFO[@]} ; do
		log_msg $CPU
	done
fi


# Disk space
# CFK - Omit landing-zone storage devices
declare -a DISK_FREE=( $(df -t ext3 -k | sed -n '2,$p' | egrep -v '/dev/sd[f-p]' | egrep -v '/dev/xvd[f-p]' ) )
for MOUNT in ${DISK_FREE[@]} ; do
	IFS=" " read FS FS_SIZE FS_USED FS_FREE FS_PCT MOUNT_POINT <<< ${MOUNT}
	if [ ${FS_FREE} -lt ${DISK_FREE_MIN} ]; then
		ERRORS=$(($ERRORS+1))
		log_err "${FS} mounted on ${MOUNT_POINT} has ${FS_FREE} kB free (Minimum ${DISK_FREE_MIN})"
	else
		log_msg "${FS} mounted on ${MOUNT_POINT} has ${FS_FREE} kB free"
	fi
	if ! sudo touch ${MOUNT_POINT}/test.$$ 2>/dev/null ; then
		ERRORS=$(($ERRORS+1))
		log_err "${FS} mounted on ${MOUNT_POINT} appears to be read-only"
	else
		log_msg "${FS} mounted on ${MOUNT_POINT} verified read/write"
	fi
	sudo rm -f ${MOUNT_POINT}/test.$$

done

# Network Interface
# ifconfig gives output like
#          RX packets:145540 errors:0 dropped:0 overruns:0 frame:0
#          TX packets:40931 errors:0 dropped:0 overruns:0 carrier:0
# use tr to change : to space, and awk to print line only if last 4 numerics add to > 0

ETH0_ERRS=$(ifconfig eth0 | tr ':' ' '  | awk '/packets/ {if($5+$7+$9+$11>0) print}')
if [ "${ETH0_ERRS}" ]; then
	ERRORS=$(($ERRORS+1))
	log_err "Interface eth0 has errors:"
	log_err "${ETH0_ERRS}"
fi

# mii-tool seems to not reliably report - need a way to verify link is 100/Full...

# Error message scan in dmesg/log files
grep -i err /var/log/messages /var/log/syslog /var/log/dmesg | grep -v 'deferred' | egrep -v 'rtc_cmos|register_vcpu_info' > /tmp/errs.$$
if [ -s /tmp/errs.$$ ]; then
	ERRORS=$(($ERRORS+1))
	log_err "Error messages found in system logs:"
	cat /tmp/errs.$$ >&2
fi
rm -f /tmp/errs.$$

# Conclusion
if [ ${ERRORS} -ne 0 ] ; then
	log_err "Total of ${ERRORS} anomalies detected."
fi
exit ${ERRORS}"""

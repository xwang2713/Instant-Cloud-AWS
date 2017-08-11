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
WSGISocketPrefix /tmp/wsgi

KeepAlive Off

<VirtualHost *:80>
   ServerName aws.hpccsystems.com
   ServerAdmin charles.kaminski@lexisnexis.com
   Redirect permanent / https://aws.hpccsystems.com
</VirtualHost>

<VirtualHost *:443>
	ServerAdmin charles.kaminski@lexisnexis.com
	ServerName aws.hpccsystems.com
	ServerAlias aws.hpccsystems.com
	DocumentRoot /home/ubuntu/sites/cloud/

	Alias /media-admin/ /usr/local/lib/python2.6/dist-packages/django/contrib/admin/static/
        Alias /favicon.ico /home/ubuntu/sites/cloud/media/images/favicon.ico

	SSLEngine On

	WSGIDaemonProcess aws.hpccsystems.com user=ubuntu group=ubuntu processes=5 threads=10 home=/home/ubuntu/sites/cloud/
	WSGIProcessGroup aws.hpccsystems.com

	WSGIScriptAlias / /home/ubuntu/sites/cloud/cloud.wsgi
	<Directory /home/ubuntu/sites/cloud/>
    	Order deny,allow
        Allow from all
	</Directory>

	#   A self-signed (snakeoil) certificate can be created by installing
	#   the ssl-cert package. See
	#   /usr/share/doc/apache2.2-common/README.Debian.gz for more info.
	#   If both key and certificate are stored in the same file, only the
	#   SSLCertificateFile directive is needed.
	SSLCertificateFile    /etc/ssl/certs/ssl-cert-snakeoil.pem
	SSLCertificateKeyFile /etc/ssl/private/ssl-cert-snakeoil.key

	BrowserMatch "MSIE [2-6]" \
		nokeepalive ssl-unclean-shutdown \
		downgrade-1.0 force-response-1.0
	# MSIE 7 and newer should be able to use keepalive
	BrowserMatch "MSIE [17-9]" ssl-unclean-shutdown
</VirtualHost>

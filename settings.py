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

from settings_base import *

DEBUG = True
TEMPLATE_DEBUG = DEBUG

# Comment out to test media from S3 Bucket
MEDIA_VERSION = ''
MEDIA_URL = 'http://127.0.0.1:8000/media/'

SESSION_COOKIE_SECURE =  False
CSRF_COOKIE_SECURE =  False

AWS_DEFAULT_INSTANCE_SIZE = 't1.micro'


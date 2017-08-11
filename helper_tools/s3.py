#---------------------------------------------------------------------------
# Copyright (C) 2012 HPCC Systems.
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
# 01/26/2012 JJC Initial code created
#---------------------------------------------------------------------------

import sys

from os import walk
from os.path import join, dirname
from fnmatch import filter as filter_
from boto import connect_s3
from boto.s3.key import Key
from boto.s3.connection import OrdinaryCallingFormat

settings_path = dirname(dirname(__file__))
sys.path.append(settings_path)

import settings

DEFAULT_FOLDER = '10'
# This is OK here.
#  Do not import the settings module inside the django framework.
#   Use -> from django.conf import settings
MEDIA_ROOT = settings.MEDIA_ROOT
MEDIA_BUCKET = settings.MEDIA_BUCKET

AWS_ACCESS_KEY_ID = 'AKIAJLEOE7GCSYISJOVQ'
AWS_SECRET_ACCESS_KEY = '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'

conn = connect_s3(AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY,
                  calling_format=OrdinaryCallingFormat())
bucket = conn.get_bucket(MEDIA_BUCKET)

# Get name of next folder to use (use default folder if none found)
folders = set()
for key in bucket.list():
    key_string = str(key.name)
    names = key_string.split('/');
    count = len(names)
    if count >= 2:
        folders.add(names[0])
if folders:
    max_folder = max(folders)
    new_folder = str(int(max_folder) + 1) + '/'
    old_folder = str(max_folder)
else:
    new_folder = DEFAULT_FOLDER + '/'
print("set MEDIA_VERSION = '%s' in the settings file." % new_folder[:-1])

# Create new keys in S3 (ignore .svn and .db files)
created_count = 0
print('using bucket name: %s' % MEDIA_BUCKET)
for root, dirs, files in walk(MEDIA_ROOT):
    for filename in filter_(files, '*.*'):
        if not '.svn' in filename and not '.db' in filename:
            current_file = join(root, filename)
            new_file = current_file.replace(MEDIA_ROOT,'')
            new_file = new_file.replace('\\','/')
            new_key = Key(bucket)
            new_key.name = '%s%s' % (new_folder, new_file)
            new_key.set_metadata('Cache-Control','max-age=7889231')
            new_key.set_contents_from_filename(current_file)
            new_key.set_acl('public-read')
            created_count += 1

# Delete old keys
deleted_count = 0
if old_folder:
    for key in bucket.list():
        if key.name.startswith(old_folder):
        # if not key.name.startswith(new_folder):
            key.delete()
            deleted_count += 1

print('created %d new keys' % created_count)
print('deleted %d old keys' % deleted_count)

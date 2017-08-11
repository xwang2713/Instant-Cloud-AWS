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

from os.path import realpath, dirname, join
from aws.userdata_script import user_data
import django

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Timothy Humphrey', 'Timothy.Humphrey@lexisnexis.com')
)

MANAGERS = ADMINS

SITE_ROOT = dirname(realpath(__file__).replace('\\','/'))
DJANGO_ROOT = dirname(realpath(django.__file__).replace('\\','/'))

# Versions
VERSIONS = {
    'front': '0.1.21',
    'back': '0.1.29',
    'hpcc': '5.4.4-1'
}

MAX_NODES = 200

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = join(SITE_ROOT, 'media/')

# Numbered version string of the folder for the media files served from the
# MEDIA_URL. Increment this number when new media files are uploaded to the
# storage provider.
MEDIA_VERSION = '12'

# Name of the storage bucket from the storage provider
MEDIA_BUCKET = 'hpccsystems-media'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = 'https://%s.s3.amazonaws.com/%s/' % (MEDIA_BUCKET, MEDIA_VERSION)
#MEDIA_URL = 'https://ec2-107-20-116-29.compute-1.amazonaws.com/media/12/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
#ADMIN_MEDIA_PREFIX = '/media/'
STATIC_URL = '/media-admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '8=(p%k1(76)_9u3i$b84@31415926535_uk65q=j0o@$v17)i3'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates"
    # or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    SITE_ROOT + '/aws/templates/',
    SITE_ROOT + '/templates/'
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.request',
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': SITE_ROOT + '/data/cloud.db',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
        'OPTIONS': {
            'timeout': 60,
        }
    }
}

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'aws'
)

# Session Settings
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
#SESSION_COOKIE_AGE = 600
SESSION_COOKIE_SECURE = not DEBUG
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# CSRF Settings
CSRF_COOKIE_SECURE = not DEBUG
CSRF_FAILURE_VIEW = 'django.views.csrf.csrf_failure'

# Amazon AWS Settings
# http://docs.amazonwebservices.com/general/latest/gr/rande.html#ec2_region

# AWS Settings
AWS_LAUNCH_CONFIGS = {
     # Virginia
     'us-east-1_m1.large_instance':{
         'ami': 'ami-a7730ecd',
         'hpcc_global_memory_size': 4096,
         'hpcc_large_mem_size': 3064,
         'install_timeout': 300,
         'instance_size': 'm1.large',
         'region': 'us-east-1',
         'info_storage': 'instance',
         'check_min_free_mem':    524288, # kb
         'check_min_free_disk':  1048576, # kb
         'check_core_count': 2,
         'user_data_script': user_data
     },    
     # Oregon
    'us-west-2_m1.large_instance':{
        'ami': 'ami-de1700bf',
        'hpcc_global_memory_size': 4096,
        'hpcc_large_mem_size': 3064,
        'install_timeout': 300,
        'instance_size': 'm1.large',
        'region': 'us-west-2',
        'info_storage': 'instance',
        'check_min_free_mem':    524288, # kb
        'check_min_free_disk':  1048576, # kb
        'check_core_count': 2,
        'user_data_script': user_data
    },    
    # N. California
    'us-west-1_m1.large_instance':{
        'ami': 'ami-3b1f705b',
        'hpcc_global_memory_size': 4096,
        'hpcc_large_mem_size': 3064,
        'install_timeout': 300,
        'instance_size': 'm1.large',
        'region': 'us-west-1',
        'info_storage': 'instance',
        'check_min_free_mem':    524288, # kb
        'check_min_free_disk':  1048576, # kb
        'check_core_count': 2,
        'user_data_script': user_data
    },
    # Ireland
     'eu-west-1_m1.large_instance':{
         'ami': 'ami-fa30ee89',
         'hpcc_global_memory_size': 4096,
         'hpcc_large_mem_size': 3064,
         'install_timeout': 300,
         'instance_size': 'm1.large',
         'region': 'eu-west-1',
         'info_storage': 'instance',
         'check_min_free_mem':    524288, # kb
         'check_min_free_disk':  1048576, # kb
         'check_core_count': 2,
         'user_data_script': user_data
     },
    # Frankfurt
     'eu-central-1_m3.large_instance':{
         'ami': 'ami-5734273b',
         'hpcc_global_memory_size': 4096,
         'hpcc_large_mem_size': 3064,
         'install_timeout': 300,
         'instance_size': 'm3.large',
         'region': 'eu-central-1',
         'info_storage': 'instance',
         'check_min_free_mem':    524288, # kb
         'check_min_free_disk':  1048576, # kb
         'check_core_count': 2,
         'user_data_script': user_data
     },
     # Singapore
      'ap-southeast-1_m1.large_instance':{
          'ami': 'ami-c22aeda1',
          'hpcc_global_memory_size': 4096,
          'hpcc_large_mem_size': 3064,
          'install_timeout': 300,
          'instance_size': 'm1.large',
          'region': 'ap-southeast-1',
          'info_storage': 'instance',
          'check_min_free_mem':    524288, # kb
          'check_min_free_disk':  1048576, # kb
          'check_core_count': 2,
          'user_data_script': user_data
     },
     # Tokyo
      'ap-northeast-1_m1.large_instance':{
          'ami': 'ami-c584a0ab',
          'hpcc_global_memory_size': 4096,
          'hpcc_large_mem_size': 3064,
          'install_timeout': 300,
          'instance_size': 'm1.large',
          'region': 'ap-northeast-1',
          'info_storage': 'instance',
          'check_min_free_mem':    524288, # kb
          'check_min_free_disk':  1048576, # kb
          'check_core_count': 2,
          'user_data_script': user_data
      },
      # Sao Paulo
       'sa-east-1_m1.large_instance':{
            'ami': 'ami-c9952ea5',
            'hpcc_global_memory_size': 4096,
            'hpcc_large_mem_size': 3064,
            'install_timeout': 300,
            'instance_size': 'm1.large',
            'region': 'sa-east-1',
            'info_storage': 'instance',
            'check_min_free_mem':    524288, # kb
            'check_min_free_disk':  1048576, # kb
            'check_core_count': 2,
            'user_data_script': user_data
        },
	# Sydney
        'ap-southeast-2_m1.large_instance':{
            'ami': 'ami-12055b71',
            'hpcc_global_memory_size': 4096,
            'hpcc_large_mem_size': 3064,
            'install_timeout': 300,
            'instance_size': 'm1.large',
            'region': 'ap-southeast-2',
            'info_storage': 'instance',
            'check_min_free_mem':    524288, # kb
            'check_min_free_disk':  1048576, # kb
            'check_core_count': 2,
            'user_data_script': user_data
        }
}

AWS_DEFAULT_LAUNCH_CONFIG = 'us-east-1_m1.large_instance'
# For getting owner ID
AWS_DEFAULT_REGION = 'us-west-2'
AWS_CLUSTER_NAME_PREFIX = 'Hpcc-'

AWS_CONFIG_FILE = '/etc/HPCCSystems/source/hpcc_config_01.xml'
AWS_ENVIRON_FILE = '/etc/HPCCSystems/environment.xml'
AWS_IPS_FILE = '/etc/HPCCSystems/source/ips.txt'

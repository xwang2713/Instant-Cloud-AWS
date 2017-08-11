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
import django

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Charles Kaminski', 'Charles.Kaminski@LexisNexis.com'),
    ('Alan Daniels', 'Alan.Daniels@LexisNexis.com'),
)

MANAGERS = ADMINS

SITE_ROOT = dirname(realpath(__file__).replace('\\','/'))
DJANGO_ROOT = dirname(realpath(django.__file__).replace('\\','/'))

# Versions
VERSIONS = {
    'front': '0.1.8',
    'back': '0.1.4',
    'hpcc': '3.4.0-1'
}

MAX_NODES = 10000

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

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = 'https://ec2-50-19-103-180.compute-1.amazonaws.com/media/'

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

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'cloud.aws'
)

DATABASES = {
    'default': {
        'NAME': 'hpcc_cloud',
        'ENGINE': 'django.db.backends.mysql',
        'USER': 'mysql_user',
        'PASSWORD': 'WS29JKL23348SWWD'
    }
}

# Session Settings
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
#SESSION_COOKIE_AGE = 600
SESSION_COOKIE_SECURE = not DEBUG
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# CSRF Settings
CSRF_COOKIE_SECURE = not DEBUG
CSRF_FAILURE_VIEW = 'django.views.csrf.csrf_failure'

# Amazon AWS Settings
AWS_REGION = 'us-east-1'
AWS_AVAILABILITY_ZONE = 'us-east-1b'
AWS_AMI_LARGE = 'ami-fbbf7892'
AWS_AMI_MICRO = 'ami-63be790a'
AWS_SIZE_LARGE = 'm1.large'
AWS_SIZE_MICRO = 't1.micro'
AWS_CLUSTER_SIZE = 10
AWS_CLUSTER_NAME_PREFIX = 'Thor-'

AWS_CONFIG_FILE = '/etc/HPCCSystems/source/hpcc_config_01.xml'
AWS_ENVIRON_FILE = '/etc/HPCCSystems/environment.xml'
AWS_IPS_FILE = '/etc/HPCCSystems/source/ips.txt'

AWS_AMI = AWS_AMI_LARGE
AWS_AMI_SIZE = AWS_SIZE_LARGE

INSTALL_WAIT_TIME = {
    'm1.large': 180,
    't1.micro': 300,
}
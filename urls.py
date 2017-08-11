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
from django.conf.urls.defaults import *
from django.contrib import admin
from django.views.static import serve
from django.conf import settings
from django.views.generic.simple import redirect_to
from aws.views import redirect_404_view

admin.autodiscover()

MEDIA_ROOT = settings.MEDIA_ROOT
MEDIA_VERSION = settings.MEDIA_VERSION
MEDIA_PATTERN = r'^media/' + MEDIA_VERSION + '(?P<path>.*)$'

handler404 = redirect_404_view

urlpatterns = patterns('',
    url(r'^$', redirect_to, {'url': '/aws/login/', 'permanent': False}),
    url(r'^aws/', include('aws.urls')),
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^cert/', include('aws.urls2')),
    url(MEDIA_PATTERN, serve, {'document_root': MEDIA_ROOT}),
)

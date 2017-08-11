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
from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template
import views

urlpatterns = patterns('',
    url(r'csr_cert/$', views.csr_cert),
    url(r'double_submit/$', views.double_submit_view, name='aws_double_submit'),
    url(r'admin/$', views.admin_view, name='aws_admin'),
    url(r'login/$', views.index_view, name='aws_login' ),   
    url(r'logout/$', views.logout_view, name='aws_logout'),
    url(r'launch/$', views.launch_view, name='aws_launch'),
    url(r'launch-advanced/$', 
        views.advanced_launch_view, name='aws_launch_advanced'),
    url(r'launch-config/(?P<config_name>.+)', views.launch_config),    
    url(r'cluster/(?P<cluster_id>\d+)/log/$', views.log_view, name='aws_log'),
    url(r'cluster/(?P<cluster_id>\d+)/ips/$', views.ips_view, name='aws_ips'),
    url(r'cluster/(?P<cluster_id>\d+)/ssh_key/file/$',
        views.download_ssh_key_view, name='aws_ssh_key_file'),
    url(r'cluster/(?P<cluster_id>\d+)/log_file/$',
        views.download_log_file_view, name='aws_log_file'),
    url(r'cluster/(?P<cluster_id>\d+)/ssh_key/$',
        views.ssh_key_view, name='aws_ssh_key'),
    url(r'cluster/(?P<cluster_id>\d+)/config_file/$',
        views.config_file_view, name='aws_config_file'),
    url(r'cluster/(?P<cluster_id>\d+)/terminate/$',
        views.terminate_view, name='aws_terminate'),
    url(r'clusters/$', views.clusters_view, name='aws_clusters'),
    url(r'security/$', views.security_view, name='aws_security'),
    url(r'comments/$', views.comments_view, name='aws_comments'),
    url(r'faqs/$', views.faqs_view, name='aws_faqs'),
    url(r'terms/$', views.terms_view, name='aws_terms'),
    url(r'getting_started/$', views.getting_started_view,
        name='aws_getting_started'),
    url(r'code-samples/$', direct_to_template,
        {'template': 'aws_code_samples.html'}, name='aws_code_samples'),
    url(r'known-issues/$', views.known_issues_view, name='aws_known_issues'),
    url(r'latest-news/$', views.latest_news_view, name='aws_latest_news'),
    url(r'change-log/$', direct_to_template,
        {'template': 'aws_change_log.html'}, name='aws_change_log'),
    #url(r'$', views.index_view, name='aws_index'),
    #url(r'^polls/(?P<poll_id>\d+)/$', 'polls.views.detail'),
)

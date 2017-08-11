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
# 02/02/2012 JJC Added admin view and decorator
#---------------------------------------------------------------------------
import cStringIO

from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.http import HttpRequest
from django.shortcuts import render_to_response, get_object_or_404
from django.shortcuts import get_list_or_404
from django.template import RequestContext, Context, loader
from django.core.urlresolvers import reverse
from django.core.servers.basehttp import FileWrapper
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.conf import settings

from boto.ec2.securitygroup import SecurityGroup
from boto.ec2 import regions, connect_to_region
from boto.ec2.instance import Instance
from boto.ec2.keypair import KeyPair

from commands import launch_cluster, terminate_cluster
from utilities import LaunchConfig, get_log_entries, is_admin
from utilities import parse_node_assignments
from models import Cluster, DoubleSubmit, FAQ
from models import Content
from forms import LoginForm, LaunchForm, LoginLaunchForm, LogForm, IndexForm
from forms import DeleteSSHKeyForm, TerminateForm, EnhancedLaunchForm
from forms import AdvancedLaunchForm
from threading import Thread
from json import dumps
from copy import copy

from datetime import datetime
from pprint import pformat

DEFAULT_LAUNCH_CONFIG = settings.AWS_DEFAULT_LAUNCH_CONFIG
LAUNCH_CONFIGS = settings.AWS_LAUNCH_CONFIGS

def csr_cert(f):
    return HttpResponse("Trustwave SSL Validation Page")

def _double_submit_decorator(f):
    def wrap(request, *args, **kwargs):
        if request.method == 'POST':
            POST = request.POST
            double_submit_token = POST['double_submit_token']
            session = request.session
            owner_id = session.get('owner_id')
            if not owner_id:
                owner_id = request.META.get('CSRF_COOKIE')

            double_submit = DoubleSubmit()
            double_submit.owner_id = owner_id
            double_submit.requesting_ip = request.META.get('REMOTE_ADDR')
            double_submit.view = f.__name__
            double_submit.date_time = double_submit_token

            try :
                double_submit.save()
            except IntegrityError:
                return HttpResponseRedirect(reverse('aws_double_submit',
                                                    args=[]))
        return f(request, *args, **kwargs)
    wrap.__doc__ = f.__doc__
    wrap.__name__ = f.__name__
    return wrap

def _login_required_decorator(f):
    def wrap(request, *args, **kwargs):
        session = request.session
        owner_id          = session.get('owner_id')
        date_time         = session.get('date_time')
        access_key_id     = session.get('access_key_id')
        secret_access_key = session.get('secret_access_key')
        if (owner_id and date_time
            and access_key_id and secret_access_key):
            return f(request, *args, **kwargs)
        else:
            return HttpResponseRedirect(reverse('aws_login', args=[]))
    wrap.__doc__ = f.__doc__
    wrap.__name__ = f.__name__
    return wrap

def _divert_if_logged_in_decorator(f):
    def wrap(request, *args, **kwargs):
        session = request.session
        owner_id          = session.get('owner_id')
        date_time         = session.get('date_time')
        access_key_id     = session.get('access_key_id')
        secret_access_key = session.get('secret_access_key')
        if (owner_id and date_time
            and access_key_id and secret_access_key):
            return HttpResponseRedirect(reverse('aws_clusters', args=[]))
        else:
            return f(request, *args, **kwargs)
    wrap.__doc__ = f.__doc__
    wrap.__name__ = f.__name__
    return wrap

def _admin_login_required_decorator(f):
    def wrap(request, *args, **kwargs):
        if is_admin(request):
            return f(request, *args, **kwargs)
        else:
            return HttpResponseRedirect(reverse('admin:index', args=[]))
    wrap.__doc__ = f.__doc__
    wrap.__name__ = f.__name__
    return wrap

def double_submit_view(request):
    return render_to_response('aws_double_submit.html',
                              context_instance = RequestContext(request))

def security_view(request):
    return render_to_response('aws_security.html',
                              context_instance = RequestContext(request))

def comments_view(request):
    return render_to_response('aws_comments.html',
                              context_instance = RequestContext(request))

@_admin_login_required_decorator
def admin_view(request):
    return render_to_response('aws_admin.html',
                              context_instance = RequestContext(request))

def logout_view(request):

    session = request.session
    session['access_key_id'] = ''
    session['secret_access_key'] = ''
    session['owner_id'] = ''
    session['date_time'] = ''

    response =  render_to_response('aws_logout.html',
                                   context_instance = RequestContext(request))

    assert(isinstance(response, HttpResponse))
    response.delete_cookie('access_key_id')
    response.delete_cookie('secret_access_key')
    response.delete_cookie('owner_id')
    response.delete_cookie('date_time')
    response.delete_cookie('csrftoken')
    response.delete_cookie('sessionid')

    return response

@_login_required_decorator
def log_view(request, cluster_id):
    session  = request.session
    owner_id = session.get('owner_id')

    cluster = get_object_or_404(Cluster, pk=cluster_id, owner_id=owner_id)

    if request.method == 'POST':
        form = LogForm(request.POST)
        if form.is_valid():
            pass
            # c_d = form.cleaned_data
            #verbose = c_d.get('verbose')
            #TODO: handled if/else verbose
        else:
            form.errors['non_field_errors'] = "Unexpected value posted"
    else:
        form = LogForm()

    try:
        log_entries = get_log_entries(cluster_id, owner_id)
    except IOError:
        log_entries = ''

    return render_to_response('aws_log.html',
                              {'cluster': cluster,'log_entries': log_entries,
                               'form': form},
                              context_instance=RequestContext(request))

def faqs_view(request):
    faqs = FAQ.objects.filter(enabled__exact=True)

    return render_to_response('aws_faqs.html', {'faqs':faqs},
                              context_instance=RequestContext(request))

def terms_view(request):
    return render_to_response('aws_terms.html',
                              context_instance = RequestContext(request))

@_login_required_decorator
def ips_view(request, cluster_id):
    session  = request.session
    owner_id = session.get('owner_id')

    cluster = get_object_or_404(Cluster, pk=cluster_id, owner_id=owner_id)
    cluster_config = cluster.configuration

    public_ips = cluster.public_ips.rstrip('\\;').split('\\;')
    public_ips = [x.strip() for x in public_ips]
    private_ips = cluster.private_ips.rstrip('\\;').split('\\;')
    private_ips = [x.strip() for x in private_ips]

    ips_dict = dict(zip(private_ips, public_ips))
    nodes = []

    if ips_dict:
        nodes = parse_node_assignments(ips_dict, cluster_config)

    return render_to_response('aws_ips.html', {'cluster':cluster,
                                               'nodes': nodes},
                              context_instance=RequestContext(request))
@_login_required_decorator
def download_ssh_key_view(request, cluster_id):
    session  = request.session
    owner_id = session.get('owner_id')

    cluster = get_object_or_404(Cluster, pk=cluster_id, owner_id=owner_id)

    ssh_key = cluster.ssh_key.encode('ascii')
    file_name = cluster.cluster_name + ".pem"

    if not ssh_key:
        raise Http404

    key_file = cStringIO.StringIO(ssh_key)

    response = HttpResponse(FileWrapper(key_file), content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename=%s' % file_name
    response['Content-Length'] = len(ssh_key)
    return response

@_login_required_decorator
def download_log_file_view(request, cluster_id):
    session  = request.session
    owner_id = session.get('owner_id')

    cluster = get_object_or_404(Cluster, pk=cluster_id, owner_id=owner_id)

    try:
        log_entries = get_log_entries(cluster_id, owner_id)
    except IOError:
        log_entries = ''

    log_entries.encode('ascii')
    date_stamp = str(datetime.now())[:10]
    file_name = '%s-%s.txt' % (date_stamp, cluster.cluster_name)

    if not log_entries: raise Http404

    log_file = cStringIO.StringIO(log_entries)

    response = HttpResponse(FileWrapper(log_file), content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename=%s' % file_name
    response['Content-Length'] = len(log_entries)
    return response

@_login_required_decorator
@_double_submit_decorator
def terminate_view(request, cluster_id):
    session  = request.session
    owner_id = session.get('owner_id')

    cluster = get_object_or_404(Cluster, pk=cluster_id, owner_id=owner_id)
    #debug = False
    #if not debug:
    #    if cluster.is_terminating == True:
    #        return HttpResponseRedirect(reverse('aws_log', args=[cluster_id]))

    if request.method == 'POST':
        form = TerminateForm(request.POST)
        if form.is_valid():
            c_d = form.cleaned_data
            terminate = c_d.get('terminate')
            if terminate:
                cluster.is_terminating = True
                cluster.is_terminate_failed = False
                cluster.save()
                _terminate_cluster_from_thread(request, cluster_id, True)
                return HttpResponseRedirect(reverse('aws_log',
                                                    args=[cluster_id]))
            else:
                form.errors['non_field_errors'] = "Unexpected value posted"
    else:
        form = TerminateForm()

    return render_to_response('aws_terminate.html',
                              {'cluster': cluster, 'form': form},
                              context_instance=RequestContext(request))

@_login_required_decorator
def ssh_key_view(request, cluster_id):
    session  = request.session
    owner_id = session.get('owner_id')

    cluster = get_object_or_404(Cluster, pk=cluster_id, owner_id=owner_id)
    ssh_key = cluster.ssh_key.encode('ascii')
    if not ssh_key:
        raise Http404

    if request.method == 'POST':
        form = DeleteSSHKeyForm(request.POST)
        if form.is_valid():
            c_d = form.cleaned_data
            delete = c_d.get('delete')
            if delete:
                cluster.ssh_key = ''
                cluster.save()
                return HttpResponseRedirect(reverse('aws_clusters', args=[]))
            else:
                form.errors['non_field_errors'] = "Unexpected value posted"
    else:
        form = DeleteSSHKeyForm()


    return render_to_response('aws_ssh_key.html',
                              {'cluster': cluster, 'form': form},
                              context_instance=RequestContext(request))

@_divert_if_logged_in_decorator
def login_view(request):
    session = request.session


    if request.method == 'POST': # If the form has been submitted...
        form = LoginForm(request.POST) # A form bound to the POST data
        if form.is_valid():
            c_d = form.cleaned_data
            if session.test_cookie_worked():
                session.delete_test_cookie()
                session['access_key_id'] = c_d.get('access_key_id')
                session['secret_access_key'] = c_d.get('secret_access_key')
                session['owner_id'] = c_d.get('owner_id')
                session['date_time'] = datetime.now()
                # Redirect after POST
                return HttpResponseRedirect(reverse('aws_clusters', args=[]))
            else:
                form.errors['non_field_errors'] = \
                    "Please enable cookies and try again"
    else:
        form = LoginForm()

    session.set_test_cookie()
    return render_to_response('aws_login.html', {'form': form,},
                              context_instance=RequestContext(request))

def _terminate_cluster_from_thread(request, cluster_id, delete_ebs_volumes):
    # Get needed info
    session = request.session
    access_key_id = session.get('access_key_id')
    secret_access_key = session.get('secret_access_key')
    owner_id = session.get('owner_id')

    debug = False

    # Terminate Cluster
    if debug:
        terminate_cluster(cluster_id, access_key_id, secret_access_key,
                          owner_id, delete_ebs_volumes)
    else:
        args = (cluster_id, access_key_id, secret_access_key, owner_id,
                delete_ebs_volumes)
        thread = Thread(target=terminate_cluster, args=args)
        thread.daemon = True
        thread.start()

def _launch_cluster_from_thread(request, node_count, roxie_nodes, launch_config):

    # Get needed info
    session = request.session
    access_key_id = session.get('access_key_id')
    secret_access_key = session.get('secret_access_key')
    owner_id = session.get('owner_id')
    region = launch_config['region']

    # Get a new cluster row id
    cluster = Cluster(owner_id=owner_id, node_count=node_count)
    cluster.requesting_ip = request.META.get('REMOTE_ADDR')
    cluster.region = region
    cluster.is_launching = True
    cluster.save()
    cluster_id = cluster.pk

    debug = False

    # Launch Cluster
    if debug:
        launch_cluster(node_count, roxie_nodes, cluster_id, launch_config,
                       access_key_id, secret_access_key, owner_id)
    else:
        args = (node_count, roxie_nodes, cluster_id, launch_config,
                access_key_id, secret_access_key,owner_id)
        thread = Thread(target=launch_cluster, args=args)
        thread.daemon = True
        thread.start()

    return cluster_id

@_login_required_decorator
@_double_submit_decorator
def launch_simple_view(request):
    session = request.session

    if request.method == 'POST': # If the form has been submitted...
        form = LaunchForm(request.POST) # A form bound to the POST data
        if form.is_valid():
            c_d = form.cleaned_data

            node_count = c_d.get('node_count')

            launch_config = LAUNCH_CONFIGS[DEFAULT_LAUNCH_CONFIG]

            cluster_id = _launch_cluster_from_thread(request, node_count, 0,
                                                     launch_config)

            return HttpResponseRedirect(reverse('aws_log', args=[cluster_id]))

    else:
        form = LaunchForm()

    session.set_test_cookie()
    max_nodes = form.fields['thor_nodes'].max_value
    return render_to_response('aws_launch_simple.html',
                              {'form': form, 'max_nodes': max_nodes},
                              context_instance=RequestContext(request))

@_login_required_decorator
@_double_submit_decorator
def launch_view(request):
    session = request.session

    if request.method == 'POST': # If the form has been submitted...
        form = EnhancedLaunchForm(request.POST) # A form bound to the POST data
        if form.is_valid():
            c_d = form.cleaned_data

            node_count = c_d.get('node_count')
            roxie_nodes = c_d.get('roxie_nodes')
            region = c_d.get('region')
            ebs_storage_ids = c_d.get('ebs_storage_ids','')


            try:
                launch_config = copy(LAUNCH_CONFIGS[region])
            except:
                raise Http404

            launch_config['ebs_storage_ids'] = ebs_storage_ids

            cluster_id = _launch_cluster_from_thread(request, node_count, roxie_nodes,
                                                     launch_config)

            return HttpResponseRedirect(reverse('aws_log', args=[cluster_id]))

    else:
        form = EnhancedLaunchForm()

    session.set_test_cookie()
    max_nodes = form.fields['thor_nodes'].max_value
    return render_to_response('aws_launch.html',
                              {'form': form, 'max_nodes': max_nodes},
                              context_instance=RequestContext(request))

@_login_required_decorator
@_double_submit_decorator
def advanced_launch_view(request):
    session = request.session

    if request.method == 'POST': # If the form has been submitted...
        form = AdvancedLaunchForm(request.POST) # A form bound to the POST data
        if form.is_valid():
            c_d = form.cleaned_data

            node_count = c_d.get('node_count')
            roxie_nodes = c_d.get('roxie_nodes')
            ebs_storage_ids = c_d.get('ebs_storage_ids','')

            try:
                launch_config = LaunchConfig()
                field_count = launch_config.get_key_count()
                keys = launch_config.get_sorted_keys()
                launch_config = dict([(keys[i], c_d.get('config%s' % i))
                                      for i in range(field_count)])
                launch_config['ebs_storage_ids'] = ebs_storage_ids
            except:
                raise Http404

            cluster_id = _launch_cluster_from_thread(request, node_count, roxie_nodes,
                                                     launch_config)
            #_write_advanced_config(launch_config, cluster_id, user_id)

            return HttpResponseRedirect(reverse('aws_log', args=[cluster_id]))

    else:
        form = AdvancedLaunchForm()

    max_nodes = form.fields['thor_nodes'].max_value
    return render_to_response('aws_launch_advanced.html',
                              {'form': form, 'max_nodes': max_nodes},
                              context_instance=RequestContext(request))


@_login_required_decorator
def config_file_view(request, cluster_id):
    session  = request.session
    owner_id = session.get('owner_id')

    cluster = get_object_or_404(Cluster, pk=cluster_id, owner_id=owner_id)

    return render_to_response('aws_config_file.html', {'cluster': cluster,},
                              context_instance=RequestContext(request))

@_login_required_decorator
def clusters_view(request):
    session           = request.session
    owner_id          = session.get('owner_id')

    clusters = Cluster.objects.filter(owner_id__exact=owner_id,
                                      is_terminated = False)

    clusters = clusters.order_by('date_created')

    return render_to_response('aws_clusters.html',
                              {'clusters':clusters},
                              context_instance=RequestContext(request))

def getting_started_view(request):
    contents = Content.objects.filter(enabled__exact=True,
                                      page__exact='Getting Started')

    return render_to_response('aws_getting_started.html', {'contents':contents},
                              context_instance=RequestContext(request))

def known_issues_view(request):
    contents = Content.objects.filter(enabled__exact=True,
                                     page__exact='Known Issues')

    return render_to_response('aws_known_issues.html', {'contents': contents},
                              context_instance=RequestContext(request))

def latest_news_view(request):
    contents = Content.objects.filter(enabled__exact=True,
                                     page__exact='Latest News')

    return render_to_response('aws_latest_news.html', {'contents': contents},
                              context_instance=RequestContext(request))

def redirect_404_view(request):

    return HttpResponseRedirect(reverse('aws_login'))

@_divert_if_logged_in_decorator
def index_view(request):
    session = request.session

    if request.method == 'POST': # If the form has been submitted...
        form = IndexForm(request.POST) # A form bound to the POST data
        if form.is_valid():
            c_d = form.cleaned_data
            if session.test_cookie_worked():
                session.delete_test_cookie()
                session['access_key_id'] = c_d.get('access_key_id')
                session['secret_access_key'] = c_d.get('secret_access_key')
                session['owner_id'] = c_d.get('owner_id')
                session['date_time'] = datetime.now()
                # Redirect after POST
                return HttpResponseRedirect(reverse('aws_clusters', args=[]))
            else:
                form.errors['non_field_errors'] = \
                    "Please enable cookies and try again"
    else:
        form = IndexForm()

    session.set_test_cookie()
    return render_to_response('aws_index.html', {'form': form,},
                              context_instance=RequestContext(request))

def launch_config(request, config_name):
    message = ''
    if request.is_ajax():
        launch_config = LaunchConfig(config_name)
        message = dumps(launch_config.get_sorted_values())
    return HttpResponse(message)

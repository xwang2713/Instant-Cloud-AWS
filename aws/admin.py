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
from aws.models import Cluster, DoubleSubmit, FAQ, Content
from django.contrib import admin
from django.utils.text import capfirst

def attrs(**kwargs):
    def attrsetter(function):
        for key, value in kwargs.items():
            setattr(function, key, value)
        return function
    return attrsetter


def truncate_field(field_name, verbose_name=None, max_length=50):

    if hasattr(field_name, '__call__'):
        getter = (lambda fun: lambda obj: fun(obj))(field_name)

        if hasattr(field_name, 'verbose_name'):
            verbose_name = field_name.verbose_name
        elif hasattr(field_name, 'short_description'):
            verbose_name = field_name.short_description

        if hasattr(field_name, 'field_name'):
            field_name = field_name.field_name
        else:
            field_name = field_name.__name__

    else:
        getter = lambda obj: getattr(obj, field_name)

    if not verbose_name:
        verbose_name = capfirst(field_name.replace('_', ' '))

    @attrs(
        short_description=verbose_name,
        admin_order_field=field_name)
    def truncated(self, obj):
        field = getter(obj)
        if len(field) <= max_length:
            return field
        return field[:(max_length - 3)] + '...'

    return truncated

class ClusterAdmin(admin.ModelAdmin):
    list_display = ('pk', 'date_created', 'cluster_name', 'node_count',
                    'owner_id', 'requesting_ip',
                    'is_launching', 'is_launched', 'is_launch_failed',
                    'is_terminating', 'is_terminated', 'is_terminate_failed')

    search_fields = ['cluster_name', 'owner_id', 'requesting_ip']
    list_filter = ('is_launching', 'is_launched', 'is_launch_failed',
                    'is_terminating', 'is_terminated', 'is_terminate_failed')

#class ClusterLogAdmin(admin.ModelAdmin):
    #list_display = ('pk', 'date_time', 'cluster', 'message_trunc')
    #message_trunc = truncate_field('message', max_length=80)

    ##list_filter = ('cluster')

    ##request.META.get('QUERY_STRING')

    ##def queryset(self, request):
        ##qs = super(MyModelAdmin, self).queryset(request)
        ##if request.user.is_superuser:
            ##return qs
        ##return qs.filter(author=request.user)

class DoubleSubmitAdmin(admin.ModelAdmin):
    list_display = ('pk', 'date_time', 'owner_id', 'requesting_ip', 'view')

class FAQAdmin(admin.ModelAdmin):
    list_display = ('order', 'pk', 'date_created',
                    'date_modified', 'enabled', 'title', 'text_trunc')
    text_trunc = truncate_field('text', max_length=80)

class ContentAdmin(admin.ModelAdmin):
    list_display = ('order', 'pk', 'enabled', 'page', 'title', 'text_trunc')
    fieldsets = (
        (None, {
            'fields': ('enabled','order', 'page', 'title', 'text')
        }),
    )
    text_trunc = truncate_field('text', max_length=80)

    list_filter = ('enabled', 'page')

admin.site.register(Cluster, ClusterAdmin)
#admin.site.register(ClusterLog, ClusterLogAdmin)
admin.site.register(DoubleSubmit, DoubleSubmitAdmin)
admin.site.register(FAQ, FAQAdmin)
admin.site.register(Content, ContentAdmin)
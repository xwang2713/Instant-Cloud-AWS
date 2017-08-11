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
from boto.exception import EC2ResponseError
from django import forms
from django.conf import settings
from commands import get_aws_owner_id
from utilities import LaunchConfig

import re

DEFAULT_REGION = settings.AWS_DEFAULT_REGION

class DeleteSSHKeyForm(forms.Form):
    delete = forms.BooleanField(widget=forms.HiddenInput(),initial=True)

class LogForm(forms.Form):
    verbose = forms.BooleanField(widget=forms.CheckboxInput(),initial=False,
                                 required=False,label='Verbose output')

class TerminateForm(forms.Form):
    terminate = forms.BooleanField(widget=forms.HiddenInput(),initial=True)
    # delete_ebs_volumes = forms.BooleanField(initial=True)
    reason = forms.CharField(max_length=100, required=False,
                                 widget=forms.TextInput(attrs={'size':'50'}),
                                 label='Reason (optional)')

class LoginForm(forms.Form):
    access_key_id = forms.CharField(max_length=100, required=True,
                        widget=forms.TextInput(attrs={'size':'50'}))
    secret_access_key = forms.CharField(max_length=100, required=True,
                        widget=forms.PasswordInput(render_value=False,
                                                   attrs={'size':'50'}))
    promo_code = forms.CharField(max_length=50, required=False,
                                 widget=forms.TextInput(attrs={'size':'25'}),
                                 label='Promo code (optional)')
    terms_of_use = forms.BooleanField(widget=forms.HiddenInput(),
                                      initial=False, required=True,
                                      error_messages={'required':'You must accept Terms of Use'})

    def clean(self):
        cleaned_data = self.cleaned_data
        access_key_id = cleaned_data.get('access_key_id')
        secret_access_key = cleaned_data.get('secret_access_key')

        if not(access_key_id and secret_access_key):
            # Pass through... errors will be raised by the individual
            #  field clean routines
            return cleaned_data
        try:
            cleaned_data['owner_id'] = get_aws_owner_id(DEFAULT_REGION,
                                                        access_key_id,
                                                        secret_access_key)

        except EC2ResponseError, e:
            raise forms.ValidationError(e.error_message)

        return cleaned_data


class IndexForm(forms.Form):
    access_key_id = forms.CharField(max_length=100, required=True,
                        widget=forms.TextInput(attrs={'size':'36'}))
    secret_access_key = forms.CharField(max_length=100, required=True,
                        widget=forms.PasswordInput(render_value=False,
                                                   attrs={'size':'36'}))  
    terms_of_use = forms.BooleanField(widget=forms.HiddenInput(),
                                      initial=False, required=True,
                                      error_messages={'required':'You must accept Terms of Use'})

    def clean(self):
        cleaned_data = self.cleaned_data
        access_key_id = cleaned_data.get('access_key_id')
        secret_access_key = cleaned_data.get('secret_access_key')

        if not(access_key_id and secret_access_key):
            # Pass through... errors will be raised by the individual
            #  field clean routines
            return cleaned_data
        try:
            cleaned_data['owner_id'] = get_aws_owner_id(DEFAULT_REGION,
                                                        access_key_id,
                                                        secret_access_key)

        except EC2ResponseError, e:
            raise forms.ValidationError(e.error_message)

        return cleaned_data


class LaunchForm(forms.Form):
    node_count = forms.IntegerField(required=True,
                        widget=forms.TextInput(attrs={'size':'8',
                                                      'readonly':True,
                                                      'style':'border: none',
                                                      'tabindex':'-1'}),
                        initial='10',
                        label='Total Nodes*')
    thor_nodes = forms.IntegerField(required=True,
                        widget=forms.TextInput(attrs={'size':'8'}),
                        initial='1',
                        label='Thor Nodes',
                        max_value = settings.MAX_NODES,
                        min_value = 0)
    roxie_nodes = forms.IntegerField(required=True,
                        widget=forms.TextInput(attrs={'size':'8'}),
                        initial='0',
                        label='Roxie Nodes',
                        max_value = settings.MAX_NODES,
                        min_value = 0)
    support_nodes = forms.IntegerField(required=True,
                        widget=forms.TextInput(attrs={'size':'8',
                                                      'readonly':True,
                                                      'style':'border: none',
                                                      'tabindex':'-1'}),
                        initial='0',
                        label='Support Nodes')

    ebs_storage_ids = forms.CharField(max_length=100, required=False,
                                widget=forms.TextInput(attrs={'size':'25'}),
                                label='Snapshot IDs (optional)')


    def _check_storage_id_chars(self, storage_id,
                                search=re.compile(r'[^a-z0-9\-]').search):
        return not bool(search(storage_id))

    def clean_ebs_storage_ids(self):
        check_storage_id_chars_ = self._check_storage_id_chars

        data = self.cleaned_data.get('ebs_storage_ids', '')
        data = data.encode('ascii', 'ignore')

        storage_ids = data
        storage_ids = storage_ids.replace(',',' ').replace(';',' ')
        storage_ids = storage_ids.split()
        for storage_id in storage_ids:
            if (not check_storage_id_chars_(storage_id) or
                not storage_id.startswith('snap')):
                message = 'Invalid Snapshot IDs.'
                raise forms.ValidationError(message)

        return data

    def clean(self):
        cleaned_data = super(LaunchForm, self).clean()
        thor_nodes = cleaned_data.get("thor_nodes")
        roxie_nodes = cleaned_data.get("roxie_nodes")
   
        if thor_nodes == 0 and roxie_nodes == 0:
            raise forms.ValidationError("The cluster must have at least one node.")
        
        return cleaned_data
    
class EnhancedLaunchForm(LaunchForm):
    REGION_CHOICES = (       
        ('us-west-2_m1.large_instance','Oregon'),
        ('us-east-1_m1.large_instance','Virginia'),              
        ('us-west-1_m1.large_instance','N. California'), 
        ('eu-west-1_m1.large_instance','Ireland'),
        ('eu-central-1_m3.large_instance','Frankfurt'),
        ('ap-southeast-1_m1.large_instance','Singapore'),
        ('ap-northeast-1_m1.large_instance','Tokyo'),
        ('sa-east-1_m1.large_instance','Sao Paulo'),
		('ap-southeast-2_m1.large_instance','Sydney')
    )
    region = forms.ChoiceField(choices=REGION_CHOICES, initial='us-west-2')
    
class AdvancedLaunchForm(LaunchForm):

    config_choices = [(key,key) for key in settings.AWS_LAUNCH_CONFIGS.keys()]
    config_choices.sort()
    config_choices.insert(0,('',''))
    base_config = forms.ChoiceField(widget = forms.Select(),
                         choices=config_choices,
                         required=True,
                         label='Select a Configuration')

    def __init__(self, *args, **kwargs):
        super(AdvancedLaunchForm, self).__init__(*args, **kwargs)
        launch_config = LaunchConfig()
        field_count = launch_config.get_key_count()
        keys = launch_config.get_sorted_keys()
        for idx in range(field_count):
            value = launch_config.get_value(idx)
            label_text = keys[idx].replace('_',' ')
            if isinstance(value,str):
                field = forms.CharField()
                if len(value) > 30:
                    widget = forms.Textarea(attrs={'cols':25, 'rows':3})
                else:
                    widget = forms.TextInput(attrs={'size':'30'})
            elif isinstance(value,int):
                field = forms.IntegerField()
                widget = forms.TextInput(attrs={'size':'30'})
            if isinstance(value,int) or isinstance(value,str):
                field.required = True
                field.widget = widget
                field.initial = ''
                field.label = label_text
                field.error_messages = {'required':'You must provide a value'}
                self.fields['config%s' % idx] = field
    def clean(self):
        c_d = super(AdvancedLaunchForm, self).clean()
        assert(isinstance(c_d, dict))

        for k, v in c_d.iteritems():
            if isinstance(v,unicode):
                v = v.replace('\r\n', '\n')
                v = v.encode('ascii', 'ignore')
                c_d[k] = v

        return c_d


class LoginLaunchForm(LoginForm, LaunchForm):
    pass

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
from django.db import models
from datetime import datetime

PAGE_CHOICES = (
    ('FAQs','FAQs'),
    ('Getting Started', 'Getting Started'),
    ('Known Issues', 'Known Issues'),
    ('Latest News', 'Latest News'),
)

class Content(models.Model):
    date_created        = models.DateTimeField(blank=True)
    date_modified       = models.DateTimeField(blank=True)
    order               = models.IntegerField(db_index=True)
    page                = models.CharField(max_length=20, db_index=True,
                                           choices=PAGE_CHOICES)
    title               = models.CharField(max_length=100, blank=True)
    text                = models.TextField()
    enabled             = models.BooleanField()

    class Meta:
        ordering = ['page', 'order', 'date_created']

    def __unicode__(self):
        return self.title

    def save(self):
        if self.date_created == None:
            self.date_created = datetime.now()
        self.date_modified = datetime.now()
        super(Content, self).save()

class FAQ(models.Model):
    date_created        = models.DateTimeField()
    date_modified       = models.DateTimeField()
    order               = models.IntegerField(db_index=True)
    title               = models.CharField(max_length=100)
    text                = models.TextField()
    enabled             = models.BooleanField()

    class Meta:
        ordering = ['order']

    def __unicode__(self):
        return self.title

    def save(self):
        if self.date_created == None:
            self.date_created = datetime.now()
        self.date_modified = datetime.now()
        super(FAQ, self).save()

class DoubleSubmit(models.Model):
    date_time         = models.DateTimeField()
    owner_id          = models.CharField(max_length=100)
    requesting_ip     = models.CharField(max_length=39)
    view              = models.CharField(max_length=40)

    def __unicode__(self):
        return '%s, %s, %s' % (self.date_time, self.owner_id, self.view)

    class Meta:
        unique_together = (("date_time", "owner_id"),)

class Cluster(models.Model):
    availability_zone   = models.CharField(max_length=20,null=True)
    date_created        = models.DateTimeField(null=True)
    date_modified       = models.DateTimeField(null=True)
    owner_id            = models.CharField(max_length=100, null=True,
                                           db_index=True)
    esp                 = models.CharField(max_length=100, null=True)
    cluster_name        = models.CharField(max_length=20, null=True,
                                           unique=True)
    region              = models.CharField(max_length=20, null=True)
    node_count          = models.IntegerField(null=True)
    ssh_key             = models.TextField(null=True)
    public_ips          = models.TextField(null=True)
    private_ips         = models.TextField(null=True)
    requesting_ip       = models.CharField(max_length=39, null=True)
    configuration       = models.TextField(null=True)
    is_launching        = models.BooleanField()
    is_launched         = models.BooleanField()
    is_launch_failed    = models.BooleanField()
    is_terminating      = models.BooleanField()
    is_terminated       = models.BooleanField()
    is_terminate_failed = models.BooleanField()

    def __unicode__(self):
        return self.cluster_name

    def reload_page(self):

        if self.is_terminate_failed:
            return False

        if self.is_terminated:
            return False

        if self.is_terminating:
            return True

        if self.is_launch_failed:
            return False

        if self.is_launched:
            return False

        if self.is_launching:
            return True

        return False

    def status(self):

        if self.is_terminate_failed:
            return 'Termination Failed'

        if self.is_terminated:
            return'Terminated'

        if self.is_terminating:
            return 'Terminating'

        if self.is_launch_failed:
            return 'Failed'

        if self.is_launched:
            return 'Ready'

        if self.is_launching:
            return 'Configuring'

        return ''

    class Meta:
        # unique_together = (('owner_id','region','cluster_name'),)
        # See sql file
        pass

    def save(self):
        if self.date_created == None:
            self.date_created = datetime.now()
        self.date_modified = datetime.now()
        super(Cluster, self).save()

    def update_status(self, status):
        if status.lower() == 'failed':
            self.is_failed = True
        self.status = status
        self.save()

# Moved cluster logs to files on the os
#class ClusterLog(models.Model):
    #date_time = models.DateTimeField()
    #cluster = models.ForeignKey(Cluster)
    #message = models.TextField()

    #def __unicode__(self):
        #return '%s, %s, %s' % (self.date_time, self.cluster, self.message[:20])

    #def save(self):
        #if self.date_time == None:
            #self.date_time = datetime.now()
        #super(ClusterLog, self).save()

#def add_new_log_entry(cluster_id, message):
    ##print message
    #c = ClusterLog(cluster_id=cluster_id, message=message)
    #c.save()

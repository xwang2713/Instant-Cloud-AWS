from datetime import datetime, timedelta
from string import join
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import urllib

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from aws.models import Cluster


TITLE_TEXT = 'HPCC Systems Instant Cloud for AWS Daily Summary'
yesterday = datetime.now() - timedelta(days=1)
yesterday_str = yesterday.strftime('%Y-%m-%d')

# Launched with the following command on production:
# python manage.py report --settings=settings_production

class Command(BaseCommand):    
    help = 'Emails the daily cluster summary report'

    def handle(self, *args, **options):                           
        
        cl_today = set(
            Cluster.objects.filter(date_created__year = yesterday.year,
                                   date_created__month = yesterday.month,
                                   date_created__day = yesterday.day))
        
        cl_change = set(
            Cluster.objects.filter(Q(date_modified__year = yesterday.year,
                                     date_modified__month = yesterday.month,
                                     date_modified__day = yesterday.day) |
                                 ((Q(is_launching = True) | 
                                   Q(is_launched  = True)) & 
                                  (Q(is_launch_failed = False) &
                                   Q(is_terminating = False) &
                                   Q(is_terminated  = False) &
                                   Q(is_terminate_failed = False)))))
                
        cl_active = set.union(cl_today,cl_change)                                                                  
      
        html = '<h3>%s</h3>' % yesterday_str
        html += '<b>Created:</b> %d' % len(cl_today)
        html += '<br/>\n'
        html += cluster_detail(cl_today)       
        send_mail(html)        
        
def cluster_detail(clusters,show_days=False):
    if len(clusters) == 0:
        return ''
    detail  = '<table border="1"><tr>'
    detail += '<th>Requesting IP Location</th><th>Nodes</th><th>Region</th>'
    detail += '<th>Owner ID</th>'
    if show_days:
        detail += '<th>Days Running</th>'
    detail += '</tr>'    
    for cluster in sorted(clusters,key=lambda cluster: cluster.date_created):
        detail += '<tr><td>' 
        detail += ip_geolocate(cluster.requesting_ip)        
        detail += '</td><td align="center">'
        detail += '%d' % cluster.node_count
        detail += '</td><td>'
        detail += cluster.region
        detail += '</td><td>'
        detail += cluster.owner_id 
        detail += '</td>'
        if show_days:
            c_d = cluster.date_created
            created = date(c_d.year, c_d.month, c_d.day)
            yesterday_date = date(yesterday.year, yesterday.month, yesterday.day)
            detail += '<td align="center">'
            detail += '%d' % (yesterday_date - created).days + '</td>'
    detail += '</tr></table>\n'
    return detail

def send_mail(html):   
    host     = 'smtp.gmail.com:587'
    fromaddr = 'hpcc.systems.svc@gmail.com'
    toaddr = ['vijay.raghavan@lexisnexis.com',
	          'flavio.villanustre@lexisnexis.com',
              'arjuna.chala@lexisnexis.com',
              'charles.kaminski@lexisnexis.com',
              'jack.coleman@lexisnexis.com',
	          'trish.mccall@lexisnexis.com']           
    password = 'thor_beat_hadoop'
    subject  = TITLE_TEXT + ': %s' % yesterday_str
        
    message = MIMEMultipart('alternative')
    message['subject'] = subject
    message['To'] = ', '.join(toaddr)
    message['From'] = fromaddr    
     
    html_body = MIMEText(html, 'html')
    message.attach(html_body)
    server = smtplib.SMTP(host) 
    server.starttls()
    server.login(fromaddr,password)
    server.sendmail(fromaddr, toaddr, message.as_string())
    server.quit()    
    
def ip_geolocate(ip_address):
    try:
        request = 'http://api.hostip.info/get_html.php?ip=' + ip_address
        response = urllib.urlopen(request).read()
        parts = response.split('\n')
        city = parts[1].split(':')
        return city[1].strip()       
    except Exception:
        return ip_address
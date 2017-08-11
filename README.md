# HPCC Systems Instant Cloud for AWS

## Installation notes:
    Ubuntu 10.04 lts

    Django 1.4.0 or greater for the signed cookies support -
        As of 12/2011 this is the dev version downloadable on the django site

        To view your version of django:
        $ python
        >>> import django
        >>> django.VERSION
        >>> exit()

    Paramiko
        $ sudo apt-get install python-paramiko

    Boto 2.2.1
	$ sudo apt-get remove --purge python-boto
	$ sudo apt-get clean
	$ wget http://boto.googlecode.com/files/boto-2.1.1.tar.gz
	$ tar xvfc boto-2.1.1.tar.gz
	$ cd boto-2.1.1
	$ sudo python setup.py install
	$ python
	>>> import boto
	>>> boto.Version
	'2.2.1'

    mod_wsgi
        $ sudo apt-get install libapache2-mod-wsgi

## Restarting Apache:
sudo /usr/sbin/apache2ctl start

## Other Notes:
   Changing the branding on the admin pages
      http://overtag.dk/wordpress/2010/04/changing-the-django-admin-site-title/
      https://code.djangoproject.com/ticket/1157

   Creating the Loading Animated GIF
      http://www.ajaxload.info/

   Source code line count:
      find . -name '*.html' | xargs wc -l
      find . -name '*.py' | xargs wc -l


## Code Changes:
CFK   - Charles Kaminski, HPCC Systems, Inc.
        Charles.Kaminski@LexisNexis.com
ATD   - Alan Daniels
        Alan.Daniels@LexisNexis.com
JJC   - Jack Coleman
	Jack.Coleman@LexisNexis.com
	Oleksandr Balyuk
	Oleksandr.Balyuk@LexisNexis.com
XW    - Xiaoming Wang (Ming)
        xiaoing.wang@lexisnexis.com

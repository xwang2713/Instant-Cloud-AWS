import os, sys
from os.path import abspath, dirname
from django.core.handlers.wsgi import WSGIHandler

path1 = dirname(abspath(__file__))
path2 = dirname(path1)
if path1 not in sys.path: sys.path.insert(0, path1)
if path2 not in sys.path: sys.path.insert(0, path2)

os.environ["DJANGO_SETTINGS_MODULE"] = "cloud.settings_dev"

application = WSGIHandler()

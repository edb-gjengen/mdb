#from django.conf.urls import patterns, include, url
from django.conf.urls.defaults import *

urlpatterns = patterns('mdb.views',
	url(r'^$', 'index'),
	url(r'^host/$', 'host'),
	url(r'^host/(<?P<host_id>\d+)/$', 'host_detail'),
)

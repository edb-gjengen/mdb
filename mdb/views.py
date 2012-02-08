from django.shortcuts import render_to_response
from django.template import RequestContext

def home(request):
    return render_to_response('index.django.html', context_instance=RequestContext(request))

def index(request):
	return render_to_response('info.django.html', context_instance=RequestContext(request))

def host(request):
	return render_to_response('host.django.html', context_instance=RequestContext(request))

def host_detail(request, host_id):
	return render_to_response('host.django.html', context_instance=RequestContext(request))

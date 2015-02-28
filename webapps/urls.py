from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^addrbook/', include('addrbook.urls')),
)

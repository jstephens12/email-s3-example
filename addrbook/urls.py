from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^$', 'addrbook.views.search', name='home'),
    url(r'^search$', 'addrbook.views.search', name='search'),
    url(r'^create$', 'addrbook.views.create', name='create'),
    url(r'^delete/(\d+)$', 'addrbook.views.delete', name='delete'),
    url(r'^edit/(\d+)$', 'addrbook.views.edit', name='edit'),
    url(r'^register$', 'addrbook.views.register', name='register'),
    # Route for built-in authentication with our own custom login page
    url(r'^login$', 'django.contrib.auth.views.login', {'template_name':'addrbook/login.html'}, name='login'),
    # Route to logout a user and send them back to the login page
    url(r'^logout$', 'django.contrib.auth.views.logout_then_login', name='logout'),
    # The following URL should match any username valid in Django and
    # any token produced by the default_token_generator
    url(r'^confirm-registration/(?P<username>[a-zA-Z0-9_@\+\-]+)/(?P<token>[a-z0-9\-]+)$', 'addrbook.views.confirm_registration', name='confirm'),
)


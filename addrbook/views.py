from django.shortcuts import render, redirect, get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.db import transaction

# Used to generate a one-time-use token to verify a user's email address
from django.contrib.auth.tokens import default_token_generator

# Used to send mail from within Django
from django.core.mail import send_mail

from addrbook.models import Entry
from addrbook.forms import RegistrationForm, CreateForm, EditForm

from datetime import datetime

from addrbook.s3 import s3_upload, s3_delete


@login_required
def search(request):
    if not 'last' in request.GET:
        return render(request, 'addrbook/search.html', {})

    last = request.GET['last']
    objects = Entry.objects.filter(last_name__istartswith=last)

    if objects.count() == 0:
        message = 'No entries with last name = "{0}"'.format(last)
        return render(request, 'addrbook/search.html', {'message': message})

    if objects.count() > 1:
        context = { 'entries': objects.all() }
        return render(request, 'addrbook/list.html', context)

    entry = objects.all()[0]
    form = EditForm(instance=entry)
    context = { 'entry': entry, 'form': form }
    return render(request, 'addrbook/edit.html', context)

@login_required
@transaction.atomic
def create(request):
    if request.method == 'GET':
        context = { 'form': CreateForm() }
        return render(request, 'addrbook/create.html', context)

    entry = Entry(created_by=request.user, creation_time=datetime.now(),
                  updated_by=request.user, update_time=datetime.now())
    create_form = CreateForm(request.POST, request.FILES, instance=entry)
    if not create_form.is_valid():
        context = { 'form': create_form }
        return render(request, 'addrbook/create.html', context)
   
    # Save the new record (note: this sets value for entry.id)
    create_form.save()


    if create_form.cleaned_data['picture']:
        url = s3_upload(create_form.cleaned_data['picture'], entry.id)
        entry.picture_url = url
        entry.save()

    message = 'Entry created'
    edit_form = EditForm(instance=entry)
    context = { 'message': message, 'entry': entry, 'form': edit_form }
    return render(request, 'addrbook/edit.html', context)

@login_required
def delete(request, id):
    if request.method != 'POST':
        message = 'Invalid request.  POST method must be used.'
        return render(request, 'addrbook/search.html', { 'message': message })

    entry = get_object_or_404(Entry, id=id)

    # Better to delete entry from DB before picture from S3
    # In case of failure, we'll leave orphaned picture
    # After entry.delete(), entry.id will be None, so save in id_to_delete
    id_to_delete = None
    if entry.picture_url:
        id_to_delete = entry.id

    entry.delete()

    if id_to_delete:
        s3_delete(id_to_delete)

    message = 'Entry for {0}, {1} has been deleted.'.format(entry.last_name, entry.first_name)
    return render(request, 'addrbook/search.html', { 'message': message })

@login_required
@transaction.atomic
def edit(request, id):
    try:
        if request.method == 'GET':
            entry = Entry.objects.get(id=id)
            form = EditForm(instance=entry)
            context = { 'entry': entry, 'form': form }
            return render(request, 'addrbook/edit.html', context)
    
        entry = Entry.objects.select_for_update().get(id=id)
        db_update_time = entry.update_time  # Copy timestamp to check after form is bound
        form = EditForm(request.POST, request.FILES, instance=entry)
        if not form.is_valid():
            context = { 'entry': entry, 'form': form }
            return render(request, 'addrbook/edit.html', context)

        # if update times do not match, someone else updated DB record while were editing
        if db_update_time != form.cleaned_data['update_time']:
            # refetch from DB and try again.
            entry = Entry.objects.get(id=id)
            form = EditForm(instance=entry)
            context = {
                'message': 'Another user has modified this record.  Re-enter your changes.',
                'entry':   entry,
                'form':    form,
            }
            return render(request, 'addrbook/edit.html', context)

        if form.cleaned_data['picture']:
            url = s3_upload(form.cleaned_data['picture'], entry.id)
            entry.picture_url = url

        # Set update info to current time and user, and save it!
        entry.update_time = datetime.now()
        entry.updated_by  = request.user
        form.save()

        # form = EditForm(instance=entry)
        context = {
            'message': 'Entry updated.',
            'entry':   entry,
            'form':    form,
        }
        return render(request, 'addrbook/edit.html', context)
    except Entry.DoesNotExist:
        context = { 'message': 'Record with id={0} does not exist'.format(id) }
        return render(request, 'addrbook/search.html', context)


@transaction.atomic
def register(request):
    context = {}

    # Just display the registration form if this is a GET request.
    if request.method == 'GET':
        context['form'] = RegistrationForm()
        return render(request, 'addrbook/register.html', context)

    # Creates a bound form from the request POST parameters and makes the 
    # form available in the request context dictionary.
    form = RegistrationForm(request.POST)
    context['form'] = form

    # Validates the form.
    if not form.is_valid():
        return render(request, 'addrbook/register.html', context)

    # At this point, the form data is valid.  Register and login the user.
    new_user = User.objects.create_user(username=form.cleaned_data['username'], 
                                        password=form.cleaned_data['password1'],
                                        first_name=form.cleaned_data['first_name'],
                                        last_name=form.cleaned_data['last_name'],
                                        email=form.cleaned_data['email'])
    # Mark the user as inactive to prevent login before email confirmation.
    new_user.is_active = False
    new_user.save()

    # Generate a one-time use token and an email message body
    token = default_token_generator.make_token(new_user)

    email_body = """
Welcome to the Simple Address Book.  Please click the link below to
verify your email address and complete the registration of your account:

  http://%s%s
""" % (request.get_host(), 
       reverse('confirm', args=(new_user.username, token)))

    send_mail(subject="Verify your email address",
              message= email_body,
              from_email="eppinger@cmu.edu",
              recipient_list=[new_user.email])

    context['email'] = form.cleaned_data['email']
    return render(request, 'addrbook/needs-confirmation.html', context)

@transaction.atomic
def confirm_registration(request, username, token):
    user = get_object_or_404(User, username=username)

    # Send 404 error if token is invalid
    if not default_token_generator.check_token(user, token):
        raise Http404

    # Otherwise token was valid, activate the user.
    user.is_active = True
    user.save()
    return render(request, 'addrbook/confirmed.html', {})

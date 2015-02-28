from django.db import models
from django.contrib.auth.models import User

class Entry(models.Model):
    last_name     = models.CharField(max_length=20)
    first_name    = models.CharField(max_length=20)
    birthday      = models.DateField(blank=True, null=True)
    address       = models.CharField(blank=True, max_length=20)
    city          = models.CharField(blank=True, max_length=20)
    state         = models.CharField(blank=True, max_length=20)
    zip_code      = models.CharField(blank=True, max_length=10)
    country       = models.CharField(blank=True, max_length=20)
    email         = models.CharField(blank=True, max_length=32)
    home_phone    = models.CharField(blank=True, max_length=16)
    cell_phone    = models.CharField(blank=True, max_length=16)
    fax           = models.CharField(blank=True, max_length=16)
    spouse_last   = models.CharField(blank=True, max_length=16)
    spouse_first  = models.CharField(blank=True, max_length=16)
    spouse_birth  = models.DateField(blank=True, null=True)
    spouse_cell   = models.CharField(blank=True, max_length=16)
    spouse_email  = models.CharField(blank=True, max_length=32)
    created_by    = models.ForeignKey(User, related_name="entry_creators")
    creation_time = models.DateTimeField()
    updated_by    = models.ForeignKey(User, related_name="entry_updators")
    update_time   = models.DateTimeField()
    picture_url   = models.CharField(blank=True, max_length=256)

    def __unicode__(self):
        return 'Entry(id=' + str(self.id) + ')'

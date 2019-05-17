from django.contrib.auth import get_user_model
from django.db import models
from django_extensions.db.models import TimeStampedModel
from events.middleware import get_current_user

User = get_user_model()

class AudithUserTime(TimeStampedModel):
    """Abstrac model to audith times and user """
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    def save(self, *args, **kwargs):
        user = get_current_user()
        if user.is_authenticated:
            if not self.pk: #: Is a create.
                self.created_by = user
            self.changed_by = user    
        super(AudithUserTime, self).save(*args, **kwargs)

    class Meta:
        abstract = True
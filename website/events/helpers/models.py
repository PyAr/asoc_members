from django.contrib.auth import get_user_model
from django.db import models
from django_extensions.db.models import TimeStampedModel
from events.middleware import get_current_user

import reversion

User = get_user_model()


class AuditUserTime(TimeStampedModel):
    """Abstrac model to audith times and user."""
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='%(app_label)s_%(class)s_created_by'
    )

    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='%(app_label)s_%(class)s_changed_by'
    )

    def save(self, *args, **kwargs):
        user = get_current_user()
        if user and user.is_authenticated:
            if not self.pk:  #: Is a create.
                self.created_by = user
            self.changed_by = user
        super(AuditUserTime, self).save(*args, **kwargs)

    class Meta:
        abstract = True


class SaveReversionMixin:
    '''Mixin to override save, wrapping with create_revision.
    To better work keep on left on inheritance.'''
    def save(self, *args, **kwargs):
        with reversion.create_revision():
            super(SaveReversionMixin, self).save(*args, **kwargs)


class ActiveManager(models.Manager):
    '''Manager to show only active instances.'''
    def get_queryset(self):
        return super().get_queryset().filter(active=True)

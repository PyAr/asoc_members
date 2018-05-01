from django.db.models.signals import post_save
from django.dispatch import receiver
from members.models import Payment

@receiver(post_save, sender=Payment)
def create_quota_from_payment(sender, instance, created, **kwargs):
    print("Inside signal!")
    if created:
        instance.to_quotes()



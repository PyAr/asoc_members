from django.db import models
from datetime import timedelta
from random import choice
from zoneinfo import ZoneInfo
import datetime

DEFAULT_SLOT_PERIOD = 60  # Minutes

# Add DifficultyLevel enum
class DifficultyLevel(models.TextChoices):
    BEGINNER = 'BEGINNER', 'Beginner'
    INTERMEDIATE = 'INTERMEDIATE', 'Intermediate'
    ADVANCED = 'ADVANCED', 'Advanced'
    EXPERT = 'EXPERT', 'Expert'


class CamperPerson(models.Model):
    """
    Personal data of somebeody attending a PyCamp.
    """
    username = models.CharField(max_length=255, unique=True)
    chat_id = models.CharField(max_length=255, unique=True, null=True, blank=True)

    def __str__(self):
        return f'Person: username: {self.username}'

class Pycamp(models.Model):
    """
    Representation of a PyCamp
    """
    headquarters = models.CharField(max_length=255, unique=True)
    init = models.DateTimeField()
    end = models.DateTimeField()
    vote_authorized = models.BooleanField(default=False)
    project_load_authorized = models.BooleanField(default=False)
    # active = models.BooleanField(default=False, null=True, blank=True)  # Transformar en property basado en las fechas
    wizard_slot_duration = models.IntegerField(default=60)  # In minutes

    def __str__(self):
        return f'Pycamp:\nheadquarters: {self.headquarters}\ninit: {self.init}\nend: {self.end}'

    def add_wizard(self, person):
        person_data, _ = CamperPerson.objects.get_or_create(username=username, chat_id=chat_id)
        camper = Camper.objects.get_or_create(pycamp=self, camper=camper)
        camper.wizard = True
        camper.save()
        return camper

    def get_wizards(self):
        return CamperPerson.objects.filter(
            camperatpycamp__pycamp=self,
            wizard=True
        )

    def get_current_wizard(self):
        """Return the Camper instance that's the currently scheduled wizard."""
        now = datetime.datetime.now(ZoneInfo("America/Argentina/Cordoba"))
        current_wizards = WizardTimeframe.objects.filter(
            pycamp=self,
            init__lte=now,
            end__gt=now
        )
        return choice(current_wizards).wizard if current_wizards.exists() else None

    def clear_wizards_schedule(self):
        WizardTimeframe.objects.filter(pycamp=self).delete()


class Camper(models.Model):
    """
    Many-to-many relationship between Pycamp and attendants (Persons).
    """
    pycamp = models.ForeignKey("Pycamp", on_delete=models.CASCADE, related_name='campers')
    person = models.ForeignKey(CamperPerson, on_delete=models.CASCADE, related_name='camperatpycamp')
    wizard = models.BooleanField(default=False)

    def is_busy(self, from_time, to_time):
        """Check if the person is busy during the given time range."""
        project_presentation_slots = Slot.objects.filter(current_wizard=self)
        for slot in project_presentation_slots:
            latest_start = max(from_time, slot.start)
            earliest_end = min(to_time, slot.get_end_time())
            if latest_start <= earliest_end:  # Overlap
                return True
        return False

class WizardTimeframe(models.Model):
    """
    Registers the timeframes in which a person is assigned as a wizard.
    """
    wizard = models.ForeignKey(Camper, on_delete=models.CASCADE)
    init = models.DateTimeField()
    end = models.DateTimeField()


class Slot(models.Model):
    """
    Time slot representation for the Projects scheduling system.
    """
    code = models.CharField(max_length=10)  # For example A1 for first slot first day
    start = models.DateTimeField()
    current_wizard = models.ForeignKey(Camper, null=True, on_delete=models.SET_NULL)

    def get_end_time(self):
        return self.start + timedelta(minutes=DEFAULT_SLOT_PERIOD)


class Project(models.Model):
    owner = models.ForeignKey(Camper, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=512)
    description = models.TextField(null=False, blank=True, default='')
    difficulty_level = models.CharField(
        max_length=20,
        choices=DifficultyLevel.choices,
        default=DifficultyLevel.BEGINNER
    )
    topic = models.CharField(max_length=255, null=True, blank=True)
    repository_url = models.URLField(null=True)
    comms_channel = models.URLField(null=True)
    presentation_slot = models.ForeignKey(Slot, null=True, blank=True, on_delete=models.SET_NULL)

    @property
    def pycamp(self):
        return self.owner.pycamp


class Vote(models.Model):
    """
    Vote representation. Many-to-many relationship.
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='votes')
    camper = models.ForeignKey(CamperPerson, on_delete=models.CASCADE)
    interest = models.BooleanField(null=True, blank=True)

    class Meta:
        unique_together = ('project', 'camper')

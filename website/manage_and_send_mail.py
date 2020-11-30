#!/usr/bin/env python

import contextlib
import io
import os
import sys
import traceback

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "website.settings")
os.environ.setdefault('DJANGO_CONFIGURATION', 'Dev')

from django.conf import settings  # noqa (import not at the top)
from django.core.mail import EmailMessage  # noqa (import not at the top)

try:
    from configurations.management import execute_from_command_line
except ImportError as exc:
    raise ImportError(
        "Couldn't import Django. Are you sure it's installed and "
        "available on your PYTHONPATH environment variable? Did you "
        "forget to activate a virtual environment?"
    ) from exc

# execute command but capturing outputs
capture = io.StringIO()
with contextlib.redirect_stdout(capture), contextlib.redirect_stderr(capture):
    try:
        execute_from_command_line(sys.argv)
    except Exception:
        # even if command crashes, just show the traceback (will be captured!)
        traceback.print_exc()

# send output by mail
recipient = "presidencia@ac.python.org.ar"
subject = "[autoreport] {}".format(" ".join(sys.argv))
text = capture.getvalue()
mail = EmailMessage(subject, text, settings.EMAIL_FROM, [recipient])
mail.send()

"""Tests for infrastructure stuff."""

import io
import logging
import os
import unittest

from unittest.mock import patch

from flake8.api.legacy import get_style_guide

FLAKE8_ROOTS = ['tests', 'members', 'events']
FLAKE8_OPTIONS = ['--max-line-length=99', '--select=E,W,F,C,N']

# avoid seeing all DEBUG logs if the test fails
for logger_name in ('flake8.plugins', 'flake8.api', 'flake8.checker', 'flake8.main'):
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)


class InfrastructureTestCase(unittest.TestCase):

    def _get_python_filepaths(self):
        """Helper to retrieve paths of Python files."""
        python_paths = []
        for root in FLAKE8_ROOTS:
            for dirpath, dirnames, filenames in os.walk(root):
                if dirpath.endswith('/migrations'):
                    continue
                for filename in filenames:
                    if filename.endswith(".py"):
                        python_paths.append(os.path.join(dirpath, filename))
        return python_paths

    def test_flake8(self):
        python_filepaths = self._get_python_filepaths()
        style_guide = get_style_guide(paths=FLAKE8_OPTIONS)
        fake_stdout = io.StringIO()
        with patch('sys.stdout', fake_stdout):
            report = style_guide.check_files(python_filepaths)
        self.assertEqual(report.total_errors, 0, "There are issues!\n" + fake_stdout.getvalue())

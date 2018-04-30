#!/bin/bash

cd website
gunicorn website.wsgi -b 0.0.0.0:8000

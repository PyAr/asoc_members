# Aplicación web para la gestión de membresías de la Asociación Civil

## Desarrollo

1. Crear un virtualenv y activarlo
2. Instalar los requirements: `pip install -r requirements.txt`
3. Instalar el proyecto en modo desarrollo: `pip install ".[dev]"`

### con Docker

```bash
make build
make makemigrations
make migrate
make start
```

If you need to create a Django's superuser:

```bash
$ make dockershell
docker-compose run --rm web /bin/bash
Starting asoc_members_postgres_1 ... done
root@f494fb4e420a:/code# cd website/
root@f494fb4e420a:/code/website# ./manage.py createsuperuser
Username (leave blank to use 'root'): admin
Email address: admin@example.com
Password:
Password (again):
Superuser created successfully.

```

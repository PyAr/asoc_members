# Aplicación web para la gestión de membresías de la Asociación Civil

## Desarrollo

1. Crear un virtualenv y activarlo
2. Instalar los requirements: `pip install -r requirements.txt`
3. Instalar el proyecto en modo desarrollo: `pip install ".[dev]"`

### con Docker

```bash
make build-dev
make start-dev
make install-dev
```

If you need to create a Django's superuser:

```bash
$ make createsuperuser
Username (leave blank to use 'root'): admin
Email address: admin@example.com
Password:
Password (again):
Superuser created successfully.
```

# Producción

### con Docker

```bash
# Actualizar el .env (copiado a partir del .env.dist)
export $(cat .env)
make build-prod
make up-prod
make migrate
make collectstatic
```

If you need to create a Django's superuser:

```bash
$ make createsuperuser
Username (leave blank to use 'root'): admin
Email address: admin@example.com
Password:
Password (again):
Superuser created successfully.
```

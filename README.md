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

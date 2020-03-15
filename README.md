# Aplicación web para la gestión de membresías de la Asociación Civil [![Build Status](https://travis-ci.org/PyAr/asoc_members.svg?branch=master)](https://travis-ci.org/PyAr/asoc_members)

## System dependencies to manage/use the project

You will need Docker in your system, here are [proper instructions to install it](https://docs.docker.com/get-docker/)

After that, you just need:

- Python 3
- Docker compose

Example to install in Debian/Ubuntu:

    sudo apt install python3 docker docker-compose


## Development

These are the normal commands used for development:

- `make bootstrap`: only needed the first time the project is setup or after service dependencies/infrastructure changed (note that in this case a proper `clean` should be issued first).

- `make test`: run all the tests

- `make run`: start all services locally, leave everything ready to play locally

- `make stop`: turn down everything (not removing all stuff, just off)

- `make clean`: stop and remove everything, no dirt left around


If you need to create a Django's superuser:

```bash
$ make createsuperuser
Username (leave blank to use 'root'): admin
Email address: admin@example.com
Password:
Password (again):
Superuser created successfully.
```

## Deploy a staging (PENDING TO CONFIGURE)

Cada merge a master genera una imagen actualizada en docker hub con el tag `latest` y automaticamente se actualiza el deploy.

## Deploy a producción.

Si se crea un tag con el formato x.y.z automaticamente se va a generar una imagen de Docker en docker hub con el tag `stable` y `prod-x.y.z` y una vez generada la imagen se va a deployar automaticamente. 




## Producción

Chequear documentación en https://github.com/PyAr/pyar_infra/

## Contribuyendo con Asoc Members

Existen varias maneras de contribuir con la web de la Asociación Civil de Python Argentina, reportando bugs, revisando que esos bugs se encuentren vigentes, etc, los pasos que se encuentran a continuación describen como realizar contribuciones a nivel de la aplicación.

Todas las contribuciones son mas que bienvenidas, pero para empezar a contribuir (con código) estos serían los siguientes pasos:

    Lee el archivo CONTRIBUTING.md para entender cómo funciona git, git-flow y tener una calidad mínima del código

    Recuerda hacer tests! (en lo posible) de los cambios que hagas, si bien la base de tests en este momento no es muy grande es algo que estaremos intentando cambiar

    Una vez tengas todo revisado haz un pull request al branch master de este proyecto https://github.com/PyAr/asoc_members/ , haciendo referencia al issue.

Una vez tu pull request sea aprobado tu código pasará a la inmortalidad de PyAr :)

FROM python:2.7.16

RUN mkdir -p /var/MicroServices/AuthService

WORKDIR /var/MicroServices/AuthService

COPY ./ /var/MicroServices/AuthService

COPY ./requirements.txt /var/MicroServices/AuthService/requirements.txt

RUN pip install -r /var/MicroServices/AuthService/requirements.txt

ENTRYPOINT python /var/MicroServices/AuthService/auth.py
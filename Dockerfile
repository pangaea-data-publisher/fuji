#FROM python:3 # No java available: Cannot use TIKA... 
### Install Java via the package manager
#RUN apt-get update && apt-get upgrade -y && apt install -y default-jdk

## OR: Use Ubuntu image with python and java pre-installed:
FROM korekontrol/ubuntu-java-python3:latest

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt setup.py ./

RUN pip3 install --no-cache-dir -r requirements.txt

COPY /fuji_server ./fuji_server

EXPOSE 1071

ENTRYPOINT ["python3"]

CMD ["-m", "fuji_server", "-c", "/usr/src/app/fuji_server/config/server.ini"]

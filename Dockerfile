# syntax=docker/dockerfile:1.5
FROM python:3.8-slim

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

### python:3 image: No java available: Cannot run TIKA... 
### Install Java via the package manager
RUN apt-get update \
  && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends default-jre-headless \
  && apt-get clean \
  && apt-get remove --purge -y default-jre-headless \ 
  && rm -rf /var/lib/apt/lists/*

## OR: Use Ubuntu image with python and java pre-installed instead (smallest):
#FROM korekontrol/ubuntu-java-python3:latest

COPY README.md pyproject.toml ./
COPY fuji_server ./fuji_server
RUN pip install --no-cache-dir .

# Docker doesn't like 'localhost'
RUN sed -i "s|localhost|0.0.0.0 |g" ./fuji_server/config/server.ini

EXPOSE 1071

ENV PYTHONPATH "${PYTHONPATH}:/usr/src/app/"

ENTRYPOINT ["python3"]

CMD ["-m", "fuji_server", "-c", "/usr/src/app/fuji_server/config/server.ini"]

FROM python:3.6

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/
RUN pip3 install python-Levenshtein rdflib==4.2.2 swagger_ui_bundle
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . /usr/src/app

EXPOSE 1071

ENTRYPOINT ["python3"]

CMD ["-m", "fuji_server"]

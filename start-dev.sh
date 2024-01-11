#!/bin/bash

sudo service php8.1-fpm start
sudo service nginx start
python -m fuji_server -c fuji_server/config/server.ini

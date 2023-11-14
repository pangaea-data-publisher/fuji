# Kara's running notes

Test URL for data: https://doi.org/10.5281/zenodo.10047401

Presentation: https://zenodo.org/records/4068347/files/FAIRsFAIR_FUJI_30092020.pdf?download=1

Working paper about metrics: https://zenodo.org/records/3934401

Paper about tool: https://doi.org/10.1016/j.patter.2021.100370

EASE repos: https://docs.google.com/spreadsheets/d/1V4jA9zWnIT4GSQc0M4ysyy2CcVC-2LYo/edit#gid=1649627670

CESSDA repos: https://github.com/cessda

## deploying LEMP

[Guide](https://www.digitalocean.com/community/tutorials/how-to-install-linux-nginx-mysql-php-lemp-stack-on-ubuntu-22-04) for reference.

```bash
sudo apt-get update
sudo apt-get install nginx
sudo ufw allow 'Nginx HTTP'
sudo service mysql start  # expects that mysql is already installed, if not run sudo apt install mysql-server
sudo apt install php8.1-fpm php-mysql
sudo apt install php8.1-curl
sudo phpenmod curl
sudo vim /etc/nginx/sites-available/fuji-dev
```

Paste:

```php
server {
    listen 9000;
    server_name fuji-dev;
    root /var/www/fuji-dev;

    index index.php;

    location / {
        try_files $uri $uri/ =404;
    }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php8.1-fpm.sock;
     }

    location ~ /\.ht {
        deny all;
    }
}
```

Link `index.php` to `/var/www/fuji-dev` by running `sudo ln /home/kmoraw/SSI/fuji/simpleclient/* /var/www/fuji-dev/`. You might need to adjust the file permissions to allow non-root writes.

Next,
```bash
sudo ln -s /etc/nginx/sites-available/fuji-dev /etc/nginx/sites-enabled/
#sudo unlink /etc/nginx/sites-enabled/default
sudo nginx -t
sudo service nginx reload
sudo service php8.1-fpm start
```

[nginx and WSL](https://stackoverflow.com/questions/61806937/nginx-running-in-wsl2-ubuntu-20-04-does-not-serve-html-page-to-windows-10-host)

Add `fuji-dev` to Windows hosts file `%windir%\system32\drivers\etc\hosts`:

```powershell
Add-Content "$env:windir\system32\drivers\etc\hosts" -value "127.0.0.1 fuji-dev" 
```

Access http://localhost:9000/, things should be fine.

## Run API

In `fuji/`, run `python -m fuji_server -c fuji_server/config/server.ini`. Access at http://localhost:1071/fuji/api/v1/ui/.

## Workflow

Things sort of start at [`fair_object_controller/assess_by_id`](fuji_server/controllers/fair_object_controller.py#36).
Here, we create a [`FAIRCheck`](fuji_server/controllers/fair_check.py) object.
This reads the metrics file during initialisation and will provide all the `check` methods.

Next, we start harvesting. This is again a method of the `FAIRCheck` object.
First, we call [`harvest_all_metadata`](fuji_server/controllers/fair_check.py#327), followed by [`harvest_re3_data`](fuji_server/controllers/fair_check.py#343) (which seems to be about Datacite) and finally [`harvest_all_data`](fuji_server/controllers/fair_check.py#357).

> It seems to me that we always scrape *all* data, but then only calculate the FAIR score based on the metrics listed in the metrics file.

Each specific evaluator, e.g. [`FAIREvaluatorLicense`](fuji_server/evaluators/fair_evaluator_license.py), is associated with a specific FsF metric. This makes it more difficult for us to reuse them. They seem to just look into the harvested data.
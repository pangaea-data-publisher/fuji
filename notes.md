# Kara's running notes

Test URL for data: https://doi.org/10.5281/zenodo.10047401

Test URL for software: https://github.com/cessda/cessda.cmv.server

Test URL for software not on GH: https://zenodo.org/records/6319836

Presentation: https://zenodo.org/records/4068347/files/FAIRsFAIR_FUJI_30092020.pdf?download=1

Working paper about metrics: https://zenodo.org/records/3934401

Paper about tool: https://doi.org/10.1016/j.patter.2021.100370

EASE repos: https://docs.google.com/spreadsheets/d/1V4jA9zWnIT4GSQc0M4ysyy2CcVC-2LYo/edit#gid=1649627670

CESSDA repos: https://github.com/cessda

## concepts

- signposting: Use typed links to make it easier for machine agents to understand what links lead to on the scholarly web. ([blog article](https://signposting.org/)). Adds a relation property to the link (`rel=author`).
- [typed links](https://www.iana.org/assignments/link-relations/link-relations.xhtml): links that have info on link relations, i.e. `rel`, also called "link relation types".

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

The metadata harvester looks through HTML markup following schema.org, Dublincore etc., through signposting/typed links (see above).
Ideally, it can find things like author information or license names that way.
It doesn't do much with GitHub, which doesn't seem to be signposted accordingly.

The data harvester is only run if the metadata harvester finds an `object_content_identifier`, which I think is supposed to point to actual content (videos, pictures, but also data files).
Then, the data harvester runs over the data file and checks things like file format.
I haven't seen it do anything yet (metadata harvester has not found an `object_content_identifier` as of date).

Each specific evaluator, e.g. [`FAIREvaluatorLicense`](fuji_server/evaluators/fair_evaluator_license.py), is associated with a specific FsF metric.
This makes it more difficult for us to reuse them.
They seem to just look into the harvested data. 
All evaluators are always called, but before they do anything, they check whether their associated metric is listed in the metrics YAML file.
Only if it is, the evaluator runs through and computes a local score.

In the end, all scores are aggregated into F, A, I, R scores.
This might be a problem for us for metrics that are associated with more than one of these.

## changes

- new requirement: `pygithub` package, using 2.1.1

## Questions

:question: for open questions

:exclamation: for answered questions

### What are all the files in `fuji_server/data` for? :question:

- :question: [`linked_vocabs/*_ontologies.json`](fuji_server/data/linked_vocabs): ...
- :question: [`access_rights.json`](fuji_server/data/access_rights.json): lists COAR, EPRINTS, EU, OPENAIRE access rights. Seems to relate to metric FsF-A1-01M, which looks for metadata item `access_level`. Is that found during metadata harvesting?
- :question: [`bioschemastypes.txt`](fuji_server/data/bioschemastypes.txt): added to `schema_org_creativeworks`, just a list of words. Not sure what happens with that.
- :question: [`creativeworktypes.txt`](fuji_server/data/creativeworktypes.txt): added to `schema_org_creativeworks`, just a list of words. Not sure what happens with that.
- :question: [`default_namespaces.txt`](fuji_server/data/default_namespaces.txt): "excluded" (whatever that means) during evaluation of FsF-I2-01M.
- :exclamation: [`file_formats.json`](fuji_server/data/file_formats.json): dictionary of scientific file formats. Used in evaluation of R1.3-02D to check the file format of the data.
- :exclamation: [`google_cache.db`](fuji_server/data/google_cache.db): Used for evaluating FsF-F4-01M (searchable in major catalogues like DataCite registry, Google Dataset, Mendeley, ...). Google Data search is queried for a PID in column `google_links`. It's a dataset with metadata about datasets that have a DOI or persistent identifier from `identifer.org`.
- :question: [`identifiers_org_resolver_data.json`](fuji_server/data/identifiers_org_resolver_data.json): Used in [`IdentifierHelper`](fuji_server/helper/identifier_helper.py). I'm not quite sure what that class does - does it extract IDs from URLs?
- :question: [`jsonldcontext.json`](fuji_server/data/jsonldcontext.json): Loaded into `Preprocessor.schema_org_context`. I think this is used in FsF-R1-01MD. No idea what it does though.
- :exclamation: [`licenses.json`](fuji_server/data/licenses.json): Used to populate `Preprocessor.license_names`, a list of SPDX licences. Used in evaluation of FsF-R1.1-01M.
- :question: [`linked_vocab.json`](fuji_server/data/linked_vocab.json): ...
- :exclamation: [`longterm_formats.json`](fuji_server/data/longterm_formats.json): This doesn't seem to be used any more (code is commented out). Instead, the info might be pulled from [`file_formats.json`](fuji_server/data/file_formats.json).
- :question: [`metadata_standards_uris.json`](fuji_server/data/metadata_standards_uris.json): ...
- :question: [`metadata_standards.json`](fuji_server/data/metadata_standards.json): Used in evaluation of FsF-R1.3-01M. Something about community specific metadata standards, whatever that means. Also, no idea how it recognises which standard it should be using?
- :exclamation: [`open_formats.json`](fuji_server/data/open_formats.json): This doesn't seem to be used any more (code is commented out). Instead, the info might be pulled from [`file_formats.json`](fuji_server/data/file_formats.json).
- :question: [`repodois.yaml`](fuji_server/data/repodois.yaml): DOIs from re3data (Datacite). No idea where these are used.
- :question: [`ResourceTypes.txt`](fuji_server/data/ResourceTypes.txt): List of content type identifiers? Seems to be loaded into `VALID_RESOURCE_TYPES` and used in evaluation of FsF-R1-01MD somehow.
- :exclamation: [`standard_uri_protocols.json`](fuji_server/data/standard_uri_protocols.json): Used for evaluating access through standardised protocols (FsF-A1-03D). Mapping of acronym to long name (e.g. FTP, SFTP, HTTP etc.)

### What is `fuji_server/harvester/repository_harvester.py` for? :question:

It defines class `RepositoryHarvester`, which doesn't seem to be used.
What's envisioned for this class?
Should we reuse it?
Is it meant for something else?

### What does `IdentifierHelper` do? :question:

...

### What do test score and test maturity mean as results?

...
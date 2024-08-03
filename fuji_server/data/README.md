# Data files

- [`linked_vocabs/*_ontologies.yaml`](./linked_vocabs)
- [`access_rights.yaml`](./access_rights.yaml): Lists COAR, EPRINTS, EU, OPENAIRE access rights. Used for evaluation of the data access level, FsF-A1-01M, which looks for metadata item `access_level`.
- [`bioschemastypes.txt`](./bioschemastypes.txt)
- [`creativeworktypes.txt`](./creativeworktypes.txt)
- [`default_namespaces.txt`](./default_namespaces.txt): Excluded during evaluation of the semantic vocabulary, FsF-I2-01M.
- [`file_formats.yaml`](./file_formats.yaml): Dictionary of scientific file formats. Used in evaluation of R1.3-02D to check the file format of the data.
- [`google_cache.db`](./google_cache.db): Used for evaluating FsF-F4-01M (searchability in major catalogues like DataCite registry, Google Dataset, Mendeley, ...). Google Data search is queried for a PID in column `google_links`. It's a dataset with metadata about datasets that have a DOI or persistent identifier from `identifer.org`.
- [`identifiers_org_resolver_data.yaml`](./identifiers_org_resolver_data.yaml): Used in [`IdentifierHelper`](fuji_server/helper/identifier_helper.py).
- [`jsonldcontext.yaml`](./jsonldcontext.yaml)
- [`licenses.yaml`](./licenses.yaml): Used to populate `Preprocessor.license_names`, a list of SPDX licences. Used in evaluation of licenses, FsF-R1.1-01M.
- [`linked_vocab.yaml`](./linked_vocab.yaml)
- [`metadata_standards_uris.yaml`](./metadata_standards_uris.yaml)
- [`metadata_standards.yaml`](./metadata_standards.yaml): Used in evaluation of community metadata, FsF-R1.3-01M.
- [`repodois.yaml`](./repodois.yaml): DOIs from re3data (Datacite).
- [`ResourceTypes.txt`](./ResourceTypes.txt)
- [`standard_uri_protocols.yaml`](./standard_uri_protocols.yaml): Used for evaluating access through standardised protocols (FsF-A1-03D). Mapping of acronym to long name (e.g. FTP, SFTP, HTTP etc.)

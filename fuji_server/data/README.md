# Data files


- [`linked_vocabs/*_ontologies.json`](./linked_vocabs)
- [`access_rights.json`](./access_rights.json): Lists COAR, EPRINTS, EU, OPENAIRE access rights. Used for evaluation of the data access level, FsF-A1-01M, which looks for metadata item `access_level`.
- [`bioschemastypes.txt`](./bioschemastypes.txt)
- [`creativeworktypes.txt`](./creativeworktypes.txt)
- [`default_namespaces.txt`](./default_namespaces.txt): Excluded during evaluation of the semantic vocabulary, FsF-I2-01M.
- [`file_formats.json`](./file_formats.json): Dictionary of scientific file formats. Used in evaluation of R1.3-02D to check the file format of the data.
- [`google_cache.db`](./google_cache.db): Used for evaluating FsF-F4-01M (searchability in major catalogues like DataCite registry, Google Dataset, Mendeley, ...). Google Data search is queried for a PID in column `google_links`. It's a dataset with metadata about datasets that have a DOI or persistent identifier from `identifer.org`.
- [`identifiers_org_resolver_data.json`](./identifiers_org_resolver_data.json): Used in [`IdentifierHelper`](fuji_server/helper/identifier_helper.py).
- [`jsonldcontext.json`](./jsonldcontext.json)
- [`licenses.json`](./licenses.json): Used to populate `Preprocessor.license_names`, a list of SPDX licences. Used in evaluation of licenses, FsF-R1.1-01M.
- [`linked_vocab.json`](./linked_vocab.json)
- [`longterm_formats.json`](./longterm_formats.json): This isn't used any more (code is commented out). Instead, the info should be pulled from [`file_formats.json`](./file_formats.json).
- [`metadata_standards.json`](./metadata_standards.json): Used in evaluation of community metadata, FsF-R1.3-01M.
- [`open_formats.json`](./open_formats.json): This isn't used any more (code is commented out). Instead, the info should be pulled from [`file_formats.json`](./file_formats.json).
- [`repodois.yaml`](./repodois.yaml): DOIs from re3data (Datacite).
- [`ResourceTypes.txt`](./ResourceTypes.txt)
- [`standard_uri_protocols.json`](./standard_uri_protocols.json): Used for evaluating access through standardised protocols (FsF-A1-03D). Mapping of acronym to long name (e.g. FTP, SFTP, HTTP etc.)

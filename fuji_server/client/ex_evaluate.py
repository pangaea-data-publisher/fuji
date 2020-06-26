#!/usr/bin/env python3

import configparser as ConfigParser
import json
import os
from pathlib import Path
from fuji_server.controllers.fair_check import FAIRCheck
from fuji_server.helper.preprocessor import Preprocessor

identifier = 'https://doi.org/10.1594/PANGAEA.902845'
#identifier='https://doi.org/10.26050/WDCC/MOMERGOMBSCMAQ'
oai_pmh = 'http://ws.pangaea.de/oai/'
debug = True

testpids=[
    '10.15493/DEFF.10000003',
    'doi:10.1038/nphys1170','doi:10.17882/42182','https://deims.org/sites/default/files/data/elter_va_fruska_gora_temperature_0.xls',
    '10.25504/FAIRsharing.2bdvmk','http://bio2rdf.org/affymetrix:1415765_at','doi:10.18129/B9.bioc.BiocGenerics',
    'https://data.noaa.gov/dataset/dataset/w00411-nos-hydrographic-survey-2015-08-15','10.6075/J0513WJD','10.7280/D1P075',
    '10.1007/s10531-013-0468-6','https://neurovault.org/images/13953/','10.17605/OSF.IO/XFWS6','https://hdl.handle.net/10411/G8MPEI',
    '10.17870/bathspa.7926890.v1','http://thredds.met.no/thredds/catalog/met.no/observations/stations/catalog.html?dataset=met.no/observations/stations/SN999',
    'https://hdl.handle.net/11676/Hz8P-d-sstjMXCmWGTY67a2O','10.24435/materialscloud:2019.0013/v2','https://www.gbif.org/dataset/4a65dba1-ff0d-4e72-aa3c-e76e48856930',
    'hdl:10037.1/10152','https://repo.clarino.uib.no/xmlui/handle/11509/95','https://hunt-db.medisin.ntnu.no/hunt-db/#/studypart/432',
    'https://www.proteinatlas.org/ENSG000002695','http://gis.ices.dk/geonetwork/srv/eng/catalog.search#/metadata/33fa648d-c4d6-4449-ac3c-dbec0f204e1d',
    'https://data.geus.dk/JupiterWWW/anlaeg.jsp?anlaegid=97389','http://tun.fi/JX.1058739','10.15468/0fxsox',
    'https://doi.pangaea.de/10.1594/PANGAEA.866933','10.17026/dans-z56-fz75','http://data.europa.eu/89h/jrc-eplca-898618b5-3306-11dd-bd11-0800200c9a66',
    'https://www.govdata.de/web/guest/suchen/-/details/temperatur-des-meerwassers-20172b0eb','doi:10.26050/WDCC/MOMERGOMBSCMAQ'
]

#testpids=['https://lithologs.net/?action=view&oid=470']
# rdf links:
#testpids=['http://bio2rdf.org/affymetrix:1415765_at','https://www.data.gv.at/katalog/dataset/b8dac7af-5c8a-4936-9abe-e1dbbdd8dd4f','https://identifiers.org/ena.embl:BN000065','https://www.ebi.ac.uk/biosamples/samples/SAMN14168013']
testpids=['https://data.gov.lv/dati/lv/dataset/covid-19','https://www.data.gouv.fr/datasets/5e7e104ace2080d9162b61d8','https://www.data.gv.at/katalog/dataset/b8dac7af-5c8a-4936-9abe-e1dbbdd8dd4f','https://datos.gob.es/es/catalogo/e05070101-evolucion-de-enfermedad-por-el-coronavirus-covid-19']
#testpids=['https://doi.org/10.26050/WDCC/MOMERGOMBSCMAQ']
#testpids=['https://data.gov.lv/dati/lv/dataset/covid-19']
#ontologies
#testpids=['https://raw.githubusercontent.com/obi-ontology/obi/v2020-04-23/obi.owl']
#testpids=['http://vocab.nerc.ac.uk/collection/L22/current/','http://purl.org/vocommons/voaf','http://purl.obolibrary.org/obo/bfo.owl']
#testpids=['http://purl.obolibrary.org/obo/bfo.owl']
#testpids=['https://raw.githubusercontent.com/BFO-ontology/BFO/v2019-08-26/bfo_classes_only.owl']
#testpids=['http://vocab.nerc.ac.uk/collection/L05/current/']
#social sciences
#testpids=['https://doi.org/10.4232/1.13491','http://dx.doi.org/10.18712/NSD-NSD2202-2-v1','http://doi.org/10.5255/UKDA-SN-854270']
#testpids=['https://doi.org/10.1594/PANGAEA.896660']
#testpids=['http://sweetontology.net/matrRockIgneous']
#clarin linguistics
#testpids=['http://hdl.handle.net/20.500.12124/7','http://hdl.handle.net/11495/DAB8-B44B-E8C8-2']
#restricted
#testpids=['https://doi.pangaea.de/10.1594/PANGAEA.919306']

startpid=None
def main():
    config = ConfigParser.ConfigParser()
    my_path = Path(__file__).parent.parent
    ini_path = os.path.join(my_path,'config','server.ini')
    config.read(ini_path)
    YAML_DIR = config['SERVICE']['yaml_directory']
    METRIC_YAML = config['SERVICE']['metrics_yaml']
    METRIC_YML_PATH = os.path.join(my_path, YAML_DIR , METRIC_YAML)
    SPDX_URL = config['EXTERNAL']['spdx_license_github']
    DATACITE_API_REPO = config['EXTERNAL']['datacite_api_repo']
    RE3DATA_API = config['EXTERNAL']['re3data_api']
    METADATACATALOG_API = config['EXTERNAL']['metadata_catalog']
    isDebug = config.getboolean('SERVICE', 'debug_mode')

    preproc = Preprocessor()
    preproc.retrieve_metrics_yaml(METRIC_YML_PATH)
    print('Total metrics defined: {}'.format(preproc.get_total_metrics()))

    isDebug = config.getboolean('SERVICE', 'debug_mode')
    preproc.retrieve_licenses(SPDX_URL, isDebug)
    preproc.retrieve_datacite_re3repos(RE3DATA_API, DATACITE_API_REPO, isDebug)
    preproc.retrieve_metadata_standards(METADATACATALOG_API, isDebug)
    preproc.retrieve_science_file_formats(isDebug)
    preproc.retrieve_long_term_file_formats(isDebug)

    print('Total SPDX licenses : {}'.format(preproc.get_total_licenses()))
    print('Total re3repositories found from datacite api : {}'.format(len(preproc.getRE3repositories())))
    print('Total subjects area of imported metadata standards : {}'.format(len(preproc.metadata_standards)))
    start=False
    for identifier in testpids:
        print (identifier)
        if identifier==startpid or not startpid:
            start=True
        if start:
            ft = FAIRCheck(uid=identifier,  test_debug=debug)
            uid_result, pid_result = ft.check_unique_persistent()
            core_metadata_result = ft.check_minimal_metatadata()
            content_identifier_included_result = ft.check_content_identifier_included()
            check_searchable_result = ft.check_searchable()
            license_result = ft.check_license()
            relatedresources_result = ft.check_relatedresources()
            access_level_result=ft.check_data_access_level()
            data_file_format_result=ft.check_data_file_format()
            data_provenance_result=ft.check_data_provenance()
            community_standards_result=ft.check_community_metadatastandards()
            data_content_metadata = ft.check_data_content_metadata()
            results = [uid_result, pid_result, core_metadata_result, content_identifier_included_result, check_searchable_result, access_level_result, license_result, data_file_format_result,data_provenance_result,community_standards_result,data_content_metadata]
            #results=[data_file_format_result]
            print(json.dumps(results, indent=4, sort_keys=True))

if __name__ == '__main__':
    main()

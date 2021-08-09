import enum
import logging
import requests as re
import pandas as pd
import os
from fuji_server.helper.catalogue_helper import MetaDataCatalogue
from fuji_server.helper.preprocessor import Preprocessor

class MetaDataCatalogueGoogleDataSearch(MetaDataCatalogue):

    islisted = False
    #apiURI = 'https://api.datacite.org/dois'
    def __init__(self,logger: logging.Logger = None):
        self.logger = logger
        self.source = self.getEnumSourceNames().GOOGLE_DATASET.value

    def query(self, pidlist):
        response = None
        if not Preprocessor.google_data_dois:
            self.logger.warning('FsF-F4-01M : Google Search DOI File does not exist, see F-UJI installation instructions')
        if not Preprocessor.google_data_urls:
            self.logger.warning('FsF-F4-01M : Google Search URL File does not exist, see F-UJI installation instructions')
        for pid in pidlist:
            if pid:
                pid = str(pid).lower()
                self.logger.info('FsF-F4-01M : Querying Google Dataset Search cache for -:' + str(pid))
                if str(pid).lower() in Preprocessor.google_data_dois:
                    self.islisted = True
                    break
                elif str(pid).lower() in Preprocessor.google_data_urls:
                    self.islisted = True
                    break

        if self.islisted:
            self.logger.info('FsF-F4-01M : Found identifier in Google Dataset Search cache -:' + str(pid))
        else:
            self.logger.info('FsF-F4-01M : Identifier not listed in Google Dataset Search cache -:' + str(pid))
            '''
        try:
            res= apiresponse = re.get(self.apiURI+'/'+pid)
            if res.status_code == 200:
                self.islisted =True
                self.logger.info('FsF-F4-01M : Querying DataCite API for -:' + str(pid))
            elif res.status_code == 404:
                self.logger.info('FsF-F4-01M : Identifier not listed in DataCite catalogue -:' + str(pid))
            else:
                self.logger.warning('FsF-F4-01M : DataCite API not available -:'+str(res.status_code))
        except Exception as e:
            self.logger.warning('FsF-F4-01M : DataCite API not available or returns errors')
        '''


        return response

    def create_lists(self, google_cache_file):
        gs = pd.read_csv(google_cache_file)
        google_doi_path = os.path.join(Preprocessor.fuji_server_dir, 'data', 'google_search_dois.txt')
        google_url_path = os.path.join(Preprocessor.fuji_server_dir, 'data', 'google_search_urls.txt')
        google_doi_set = set(gs['doi'].astype(str).str.lower().unique())
        google_url_set = set(gs['url'].astype(str).str.lower().unique())
        fu = open(google_url_path, "w")
        fu.write('\n'.join(google_url_set))
        fu.close()
        fd = open(google_doi_path, "w")
        fd.write('\n'.join(google_doi_set))
        fd.close()

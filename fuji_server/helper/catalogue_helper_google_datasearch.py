import enum
import logging
import requests as re

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

# -*- coding: utf-8 -*-
import logging
import requests as re

from fuji_server.helper.catalogue_helper import MetaDataCatalogue


class MetaDataCatalogueDataCite(MetaDataCatalogue):

    islisted = False
    apiURI = 'https://api.datacite.org/dois'

    def __init__(self, logger: logging.Logger = None):
        self.logger = logger
        self.source = self.getEnumSourceNames().DATACITE.value

    def query(self, pid):
        response = None
        try:
            res = apiresponse = re.get(self.apiURI + '/' + pid, timeout=5)
            self.logger.info('FsF-F4-01M : Querying DataCite API for -:' + str(pid))
            if res.status_code == 200:
                self.islisted = True
                self.logger.info('FsF-F4-01M : Found identifier in DataCite catalogue -:' + str(pid))
            elif res.status_code == 404:
                self.logger.info('FsF-F4-01M : Identifier not listed in DataCite catalogue -:' + str(pid))
            else:
                self.logger.error('FsF-F4-01M : DataCite API not available -:' + str(res.status_code))
        except Exception as e:
            self.logger.error('FsF-F4-01M : DataCite API not available or returns errors -:' + str(e))

        return response

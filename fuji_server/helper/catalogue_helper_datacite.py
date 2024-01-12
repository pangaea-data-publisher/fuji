# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import logging

import requests

from fuji_server.helper.catalogue_helper import MetaDataCatalogue


class MetaDataCatalogueDataCite(MetaDataCatalogue):
    """A class to access Datacite  metadata catalogue
    Attributes
    ----------
    isListed : bool
        Boolean to check whether the metadata is listed in the metadata catalog
    apiURI : str
        The URI for API of metadata catalogue

    Methods
    -------
    query(pid)
        Method to check whether the metadata given by PID is listed in Datacite
    """

    islisted = False
    apiURI = "https://api.datacite.org/dois"

    def __init__(self, logger: logging.Logger | None = None):
        """
        Parameters
        ----------
        logger: logging.Logger, option
            Logger instance, default is None
        """
        self.logger = logger
        self.source = self.getEnumSourceNames().DATACITE.value

    def query(self, pid):
        """Method to check whether the metadata given by PID is listed in Datacite
        Parameters
        ----------
        pid:str
            A PID

        Returns
        -------
        response
            session response
        """
        response = None
        try:
            res = requests.get(self.apiURI + "/" + pid, timeout=5)
            self.logger.info("FsF-F4-01M : Querying DataCite API for -:" + str(pid))
            if res.status_code == 200:
                self.islisted = True
                self.logger.info("FsF-F4-01M : Found identifier in DataCite catalogue -:" + str(pid))
            elif res.status_code == 404:
                self.logger.info("FsF-F4-01M : Identifier not listed in DataCite catalogue -:" + str(pid))
            else:
                self.logger.error("FsF-F4-01M : DataCite API not available -:" + str(res.status_code))
        except Exception as e:
            self.logger.error("FsF-F4-01M : DataCite API not available or returns errors -:" + str(e))

        return response

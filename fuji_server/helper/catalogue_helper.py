import enum
import logging


class MetaDataCatalogue:
    """A base class of to access a metadata catalogue
    Attributes
    ----------
    apiURI : str
        The URI for API of metadata catalogue
    Sources : enum.Enum
        Enum class of metadata catalogs

    Methods
    -------
    getEnumSourceNames()
        Class method to return Sources
    query(pid)
        Method to access the metadata catalog given a parameter of PID
    """

    apiURI = None

    # Using enum class create enumerations of metadata catalogs

    class Sources(enum.Enum):
        DATACITE = "DataCite Registry"
        GOOGLE_DATASET = "Google Dataset Search"
        MENDELEY_DATA = "Mendeley Data"

    def __init__(self, logger: logging.Logger | None = None):
        """
        Parameters
        ----------
        logger: logging.Logger, option
            Logger instance, default is None
        """
        self.logger = logger
        self.islisted = False
        self.source = None

    @classmethod
    def getEnumSourceNames(cls) -> Sources:
        """Class method to return Sources"""
        return cls.Sources

    def query(self, pid):
        """Method to access the metadata catalog given a parameter of PID
        Parameters
        ----------
        pid:str
            Persistence Identifier

        Returns
        -------
        response
            session response
        """
        response = None
        return response

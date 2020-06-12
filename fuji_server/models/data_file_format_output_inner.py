# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from fuji_server.models.base_model_ import Model
from fuji_server import util


class DataFileFormatOutputInner(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """
    def __init__(self, file_uri: str=None, mime_type: str=None, file_type: str=None, is_long_term_format: bool=False, is_open_format: bool=False):  # noqa: E501
        """DataFileFormatOutputInner - a model defined in Swagger

        :param file_uri: The file_uri of this DataFileFormatOutputInner.  # noqa: E501
        :type file_uri: str
        :param mime_type: The mime_type of this DataFileFormatOutputInner.  # noqa: E501
        :type mime_type: str
        :param file_type: The file_type of this DataFileFormatOutputInner.  # noqa: E501
        :type file_type: str
        :param is_long_term_format: The is_long_term_format of this DataFileFormatOutputInner.  # noqa: E501
        :type is_long_term_format: bool
        :param is_open_format: The is_open_format of this DataFileFormatOutputInner.  # noqa: E501
        :type is_open_format: bool
        """
        self.swagger_types = {
            'file_uri': str,
            'mime_type': str,
            'file_type': str,
            'is_long_term_format': bool,
            'is_open_format': bool
        }

        self.attribute_map = {
            'file_uri': 'file_uri',
            'mime_type': 'mime_type',
            'file_type': 'file_type',
            'is_long_term_format': 'is_long_term_format',
            'is_open_format': 'is_open_format'
        }
        self._file_uri = file_uri
        self._mime_type = mime_type
        self._file_type = file_type
        self._is_long_term_format = is_long_term_format
        self._is_open_format = is_open_format

    @classmethod
    def from_dict(cls, dikt) -> 'DataFileFormatOutputInner':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The DataFileFormat_output_inner of this DataFileFormatOutputInner.  # noqa: E501
        :rtype: DataFileFormatOutputInner
        """
        return util.deserialize_model(dikt, cls)

    @property
    def file_uri(self) -> str:
        """Gets the file_uri of this DataFileFormatOutputInner.


        :return: The file_uri of this DataFileFormatOutputInner.
        :rtype: str
        """
        return self._file_uri

    @file_uri.setter
    def file_uri(self, file_uri: str):
        """Sets the file_uri of this DataFileFormatOutputInner.


        :param file_uri: The file_uri of this DataFileFormatOutputInner.
        :type file_uri: str
        """

        self._file_uri = file_uri

    @property
    def mime_type(self) -> str:
        """Gets the mime_type of this DataFileFormatOutputInner.


        :return: The mime_type of this DataFileFormatOutputInner.
        :rtype: str
        """
        return self._mime_type

    @mime_type.setter
    def mime_type(self, mime_type: str):
        """Sets the mime_type of this DataFileFormatOutputInner.


        :param mime_type: The mime_type of this DataFileFormatOutputInner.
        :type mime_type: str
        """

        self._mime_type = mime_type

    @property
    def file_type(self) -> str:
        """Gets the file_type of this DataFileFormatOutputInner.


        :return: The file_type of this DataFileFormatOutputInner.
        :rtype: str
        """
        return self._file_type

    @file_type.setter
    def file_type(self, file_type: str):
        """Sets the file_type of this DataFileFormatOutputInner.


        :param file_type: The file_type of this DataFileFormatOutputInner.
        :type file_type: str
        """

        self._file_type = file_type

    @property
    def is_long_term_format(self) -> bool:
        """Gets the is_long_term_format of this DataFileFormatOutputInner.


        :return: The is_long_term_format of this DataFileFormatOutputInner.
        :rtype: bool
        """
        return self._is_long_term_format

    @is_long_term_format.setter
    def is_long_term_format(self, is_long_term_format: bool):
        """Sets the is_long_term_format of this DataFileFormatOutputInner.


        :param is_long_term_format: The is_long_term_format of this DataFileFormatOutputInner.
        :type is_long_term_format: bool
        """

        self._is_long_term_format = is_long_term_format

    @property
    def is_open_format(self) -> bool:
        """Gets the is_open_format of this DataFileFormatOutputInner.


        :return: The is_open_format of this DataFileFormatOutputInner.
        :rtype: bool
        """
        return self._is_open_format

    @is_open_format.setter
    def is_open_format(self, is_open_format: bool):
        """Sets the is_open_format of this DataFileFormatOutputInner.


        :param is_open_format: The is_open_format of this DataFileFormatOutputInner.
        :type is_open_format: bool
        """

        self._is_open_format = is_open_format
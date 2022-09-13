# -*- coding: utf-8 -*-

# MIT License
#
# Copyright (c) 2020 PANGAEA (https://www.pangaea.de/)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import json
import jmespath
from pyld import jsonld

from fuji_server.helper.metadata_collector import MetaDataCollector
from fuji_server.helper.preprocessor import Preprocessor
from fuji_server.helper.request_helper import RequestHelper, AcceptTypes


class MetaDataCollectorSchemaOrg(MetaDataCollector):
    """
    A class to collect the schema.org. metadata form the data. This class is child class of MetadataCollector.

    ...

    Attributes
    ----------
    source_name : str
        Source name of metadata
    pid_url : str
        Persistance Identifier URL
    SCHEMA_ORG_CONTEXT : list
        A list of schema.org context

    Methods
    --------
    parse_metadata(ls)
        Method to parse the schema.org metadata given JSON-LD.
    compact_jsonld(jsonld)
        Method to have the Compacted JSON-LD

    """
    source_name = None
    SCHEMA_ORG_CONTEXT = Preprocessor.get_schema_org_context()
    SCHEMA_ORG_CREATIVEWORKS = Preprocessor.get_schema_org_creativeworks()
    def __init__(self, sourcemetadata, mapping, loggerinst, pidurl, source = None):
        """
        Parameters
        ----------
        sourcemetadata : str
            Source of metadata
        mapping : Mapper
            Mapper to metedata sources
        loggerinst : logging.Logger
            Logger instance
        pidurl : str
            PID URL
        source : str
            Source (e.g. typed links etc..)
        """
        #self.is_pid = ispid
        self.pid_url = pidurl
        self.source_name = source
        super().__init__(logger=loggerinst, mapping=mapping, sourcemetadata=sourcemetadata)

    def parse_metadata(self, ls=None):
        """Parse the metadata given JSON-LD schema.org.

        Parameters
        ----------
        ls: str
            License

        Returns
        ------
        str
            a string of source name
        dict
            a dictionary of metadata in RDF graph
        """
        jsnld_metadata = {}
        self.content_type = 'application/ld+json'
        #Don't trust e.g. non creative work schema.org
        trusted = True
        ext_meta = None
        if self.source_metadata:
            if not self.source_name:
                self.source_name = self.getEnumSourceNames().SCHEMAORG_EMBED.value
            # in case two or more JSON-LD strings are embedded
            if len(self.source_metadata) > 1:
                self.logger.info('FsF-F2-01M : Found more than one JSON-LD embedded in landing page try to identify Dataset or CreativeWork type')
                for meta_rec in self.source_metadata:
                    if str(meta_rec.get('@type')).lower() in ['dataset']:
                        ext_meta = meta_rec
                        break
                    if str(meta_rec.get('@type')).lower() in self.SCHEMA_ORG_CREATIVEWORKS:
                        ext_meta = meta_rec

            if not ext_meta:
                ext_meta = self.source_metadata[0]
        elif self.pid_url:
            self.source_name = self.getEnumSourceNames().SCHEMAORG_NEGOTIATE.value
            # TODO (IMPORTANT) PID agency may support Schema.org in JSON-LD
            # TODO (IMPORTANT) validate schema.org
            # fallback, request (doi) metadata specified in schema.org JSON-LD
            requestHelper: RequestHelper = RequestHelper(self.pid_url, self.logger)
            requestHelper.setAcceptType(AcceptTypes.schemaorg)
            neg_source, ext_meta = requestHelper.content_negotiate('FsF-F2-01M')
        if isinstance(ext_meta, dict):
            self.setLinkedNamespaces(ext_meta)
            self.logger.info('FsF-F2-01M : Trying to extract schema.org JSON-LD metadata from -: {}'.format(
                self.source_name))
            # TODO check syntax - not ending with /, type and @type
            # TODO (important) extend mapping to detect other pids (link to related entities)?
            try:
                #if ext_meta['@context'] in check_context_type['@context'] and ext_meta['@type'] in check_context_type["@type"]:
                if str(ext_meta.get('@context')).find('://schema.org') > -1:
                    schemaorgns = 'schema'
                    if isinstance(ext_meta.get('@context'), dict):
                        for contextname, contexturi in ext_meta.get('@context').items():
                            if contexturi.endswith('schema.org/'):
                                schemaorgns = contextname
                    ext_meta = json.loads(json.dumps(ext_meta).replace('"' + schemaorgns + ':', '"'))
                    #special case #1
                    if ext_meta.get('mainEntity'):
                        self.logger.info('FsF-F2-01M : \'MainEntity\' detected in JSON-LD, trying to identify its properties')
                        for mainEntityprop in ext_meta.get('mainEntity'):
                            ext_meta[mainEntityprop] = ext_meta.get('mainEntity').get(mainEntityprop)

                    if isinstance(ext_meta.get('@type'), list):
                        ext_meta['@type'] = ext_meta.get('@type')[0]

                    if not ext_meta.get('@type'):
                        self.logger.info(
                            'FsF-F2-01M : Found JSON-LD but seems to be a schema.org object but has no context type')

                    elif str(ext_meta.get('@type')).lower() not in self.SCHEMA_ORG_CONTEXT:
                        trusted = False
                        self.logger.info(
                            'FsF-F2-01M : Found JSON-LD but will not use it since it seems not to be a schema.org object based on the given context type -:'
                            + str(ext_meta.get('@type')))
                    elif str(ext_meta.get('@type')).lower() not in self.SCHEMA_ORG_CREATIVEWORKS:
                        trusted = False
                        self.logger.info(
                            'FsF-F2-01M : Found schema.org JSON-LD but will not use it since it seems not to be a CreativeWork like research data object -:'+str(ext_meta.get('@type')))
                    else:
                        self.logger.info(
                            'FsF-F2-01M : Found schema.org JSON-LD which seems to be valid, based on the given context type -:'
                            + str(ext_meta.get('@type')))

                        self.namespaces.append('http://schema.org/')
                        jsnld_metadata = jmespath.search(self.metadata_mapping.value, ext_meta)
                    # TODO all properties with null values extracted through jmespath should be excluded
                    if jsnld_metadata.get('creator') is None:
                        #TODO: handle None values for first and last name
                        first = jsnld_metadata.get('creator_first')
                        last = jsnld_metadata.get('creator_last')
                        if last:
                            if isinstance(first, list) and isinstance(last, list):
                                if len(first) == len(last):
                                    names = [str(i) + ' ' + str(j) for i, j in zip(first, last)]
                                    jsnld_metadata['creator'] = names
                            else:
                                jsnld_metadata['creator'] = [str(first) + ' ' + str(last)]

                    #TODO instead of custom check there should a valdiator to evaluate the whole schema.org metadata
                    invalid_license = False
                    if jsnld_metadata.get('license'):
                        self.logger.info('FsF-R1.1-01M : License metadata found (schema.org) -: {}'.format(
                            jsnld_metadata.get('license')))

                        if isinstance(jsnld_metadata.get('license'), list):
                            jsnld_metadata['license'] = jsnld_metadata['license'][0]
                        if isinstance(jsnld_metadata.get('license'), dict):
                            ls_type = jsnld_metadata.get('license').get('@type')
                            if ls_type == 'CreativeWork':
                                ls = jsnld_metadata.get('license').get('url')
                                if not ls:
                                    ls = jsnld_metadata.get('license').get('name')
                                if ls:
                                    jsnld_metadata['license'] = ls
                                else:
                                    invalid_license = True
                            else:
                                invalid_license = True
                    if invalid_license:
                        self.logger.warning(
                            'FsF-R1.1-01M : Looks like schema.org representation of license is incorrect, skipping the test.'
                        )
                        jsnld_metadata['license'] = None

                    # filter out None values of related_resources

                    if jsnld_metadata.get('related_resources'):
                        relateds = [d for d in jsnld_metadata['related_resources'] if d['related_resource'] is not None]
                        if relateds:
                            jsnld_metadata['related_resources'] = relateds
                            self.logger.info('FsF-I3-01M : {0} related resource(s) extracted from -: {1}'.format(
                                len(jsnld_metadata['related_resources']), self.source_name))
                        else:
                            del jsnld_metadata['related_resources']
                            self.logger.info('FsF-I3-01M : No related resource(s) found in Schema.org metadata')

                    # TODO quick-fix, expand mapping expression instead
                    if jsnld_metadata.get('object_size'):
                        #print(jsnld_metadata.get('object_size'))
                        if isinstance(jsnld_metadata['object_size'], dict):
                            jsnld_metadata['object_size'] = str(jsnld_metadata['object_size'].get('value'))

                        #jsnld_metadata['object_size'] = str(jsnld_metadata['object_size'].get('value')) + ' '+ jsnld_metadata['object_size'].get('unitText')

                else:
                    self.logger.info('FsF-F2-01M : Found JSON-LD but record is not of type schema.org based on context -: '+str(ext_meta.get('@context')))

            except Exception as err:
                #print(err.with_traceback())
                self.logger.info('FsF-F2-01M : Failed to parse JSON-LD schema.org -: {}'.format(err))
        else:
            self.logger.info('FsF-F2-01M : Could not identify JSON-LD schema.org metadata from dict')



        if not trusted:
            jsnld_metadata = {}
        return self.source_name, jsnld_metadata

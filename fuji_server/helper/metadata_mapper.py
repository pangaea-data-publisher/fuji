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

from enum import Enum

class Mapper(Enum):
    ## ============================ CONFIGURATIONS ============================ ##
    # List of PIDS e.g. those listed in datacite schema
    VALID_PIDS = ['ark','arxiv','bioproject','biosample','doi', 'ensembl','genome','gnd','handle','lsid','pmid','pmcid','purl', 'refseq','sra','uniprot','urn']

    #identifiers.org pattern
    #TODO: check if this is needed.. if so ..complete and add check to FAIRcheck
    IDENTIFIERS_PIDS=r'https://identifiers.org/[provider_code/]namespace:accession'

    #CMMI capability maturity levels
    MATURITY_LEVELS = {0: 'incomplete', 1: 'initial', 2: 'managed', 3: 'defined', 4: 'quantitatively managed',5: 'optimizing'}


    # reference metadata elements (used by FUJI)
    #['creator','license','related_resources'] --> list type
    # datacite_client --> retrieve re3data records
    # TODO include data types of all reference elements
    REFERENCE_METADATA_LIST = ['object_identifier', 'creator', 'title', 'publisher', 'publication_date', 'summary', 'keywords',
                 'object_content_identifier', 'access_level', 'access_free','policy','related_resources','provenance_general',
                 'measured_variable', 'method', 'creation_date', 'contributor','version', 'license','data_file_format', 'file_format_only',
                 'object_type', 'data_size','datacite_client', 'modified_date','created_date','right_holder', 'object_size']

    # core metadata elements (FsF-F2-01M)
    REQUIRED_CORE_METADATA = ['creator', 'title', 'publisher', 'publication_date', 'summary', 'keywords','object_identifier','object_type']


    ## ============================ METADATA MAPPINGS ============================ ##
    #https://www.dublincore.org/webinars/2015/openaire_guidelines_promoting_repositories_interoperability_and_supporting_open_access_funder_mandates/slides.pdf
    ACCESS_RIGHT_CODES = {'creativecommons': 'public', 'creative commons': 'public',
                    'c_abf2': 'public', 'c_f1cf': 'embargoed', 'c_16ec': 'restricted', 'c_14cb': 'metadataonly',
                    'OpenAccess': 'public', 'ClosedAccess': 'closed', 'RestrictedAccess': 'restricted',
                    'NON_PUBLIC': 'restricted', 'OP_DATPRO': 'embargoed', 'PUBLIC': 'public',
                    'RESTRICTED': 'restricted', 'SENSITIVE': 'restricted', 'embargoedAccess':'embargoed'
                    }

    #https://en.wikipedia.org/wiki/List_of_archive_formats#cite_ref-MIME_type_2-3
    # only consider mime types registered with IANA: https://www.iana.org/assignments/media-types/media-types.xhtml
    ARCHIVE_COMPRESS_MIMETYPES =['application/gzip','application/zstd','application/octet-stream','application/vnd.ms-cab-compressed','application/zip','application/x-gzip']

    # https://www.dublincore.org/specifications/dublin-core/dcmi-terms/
    # dc: rights, dcterm: accessRights, rightsHolder?
    # license: Recommended practice is to identify the license document with a URI. If this is not possible or feasible, a literal value that identifies the license may be provided.
    DC_MAPPING = {'object_identifier': 'identifier', 'creator': 'creator', 'title': 'title', 'contributor' : 'contributor',
              'publisher': 'publisher', 'publication_date': ['date','available', 'issued'], 'summary': 'abstract',
              'keywords': 'subject', 'object_type': 'type','modified_date': 'modified','created_date' : 'created',
              'license': 'license', 'file_format_only': 'format', 'access_level':['rights','accessRights'],
                  'date_available':'available','provenance_general':'provenance',
                'related_resources':['relation','source','references']}

    # https://ogp.me/
    # og:url ->The canonical URL of your object that will be used as its permanent ID in the graph (assume this is fuji:object_indentifier)
    OG_MAPPING = {'title': 'og:title', 'object_identifier': 'og:url', 'summary': 'og:description',
              'object_type': 'og:type', 'publisher': 'og:site_name'}

    # Schema.org
    # conditionsOfAccess, usageInfo?, isAccessibleForFree
    ## A license document that applies to this content, typically indicated by URL.
    SCHEMAORG_MAPPING = '{title: name, object_type: "@type", '\
                            'publication_date: datePublished."@value" || datePublished || dateCreated, '\
                            'modified_date: dateModified."@value" ||dateModified, ' \
                           'creator: creator[?"@type" ==\'Person\'].name || creator[?"@type" ==\'Organization\'].name || author[*].name || creator.name || author.name, ' \
                           'creator_first: creator[*].givenName || author[*].givenName || creator.givenName || author.givenName,' \
                           'creator_last: creator[*].familyName || author[*].familyName || creator.familyName || author.familyName,' \
                           'contributor: contributor[*].name || contributor[*].familyName, ' \
                           'right_holder: copyrightHolder[*].name || copyrightHolder[*].familyName, ' \
                           'publisher: publisher.name || provider, license: license."@id" || license[?"@type" ==\'CreativeWork\'].id || license[?"@type" ==\'CreativeWork\'].url || license[?"@type" ==\'CreativeWork\'].name || license, ' \
                           'summary: description, keywords: keywords, ' \
                           'object_identifier: (identifier.value || identifier[0].value || identifier || "@id") || (url || url."@id") , ' \
                            'access_level: conditionsOfAccess, ' \
                            'access_free:  (isAccessibleForFree || free), ' \
                            'measured_variable: variableMeasured[*].name || variableMeasured , object_size: size,' \
                            'related_resources: [{related_resource: (isPartOf."@id" || isPartOf[0]."@id" || isPartOf.url || isPartOf[0].url || isPartOf), relation_type: \'isPartOf\'}, ' \
                            '{related_resource: (includedInDataCatalog."@id" || includedInDataCatalog[0]."@id" || includedInDataCatalog.url || includedInDataCatalog[0].url || includedInDataCatalog.name || includedInDataCatalog[0].name || includedInDataCatalog), relation_type: \'isPartOf\'}, ' \
                            '{related_resource: (subjectOf."@id" || subjectOf[0]."@id" || subjectOf.url ||subjectOf[0].url || subjectOf.name || subjectOf[0].name || subjectOf), relation_type: \'isReferencedBy\'},' \
                            '{related_resource: (isBasedOn."@id" || isBasedOn[0]."@id" || isBasedOn.url || isBasedOn[0].url || isBasedOn) , relation_type: \'isBasedOn\'} , ' \
                            '{related_resource: "@reverse".isBasedOn[0]."@id" || "@reverse".isBasedOn[0].url || isBasedOn , relation_type: \'isBasisFor\'} ], ' \
                            'object_content_identifier: (distribution[*].{url: contentUrl, type: (encodingFormat || fileFormat), size: (contentSize || fileSize), profile: schemaVersion} || [distribution.{url: contentUrl, type: (encodingFormat || fileFormat), size: (contentSize || fileSize), profile: schemaVersion}])}'
    # 'related_resources: [{related_resource: isPartOf, relation_type: \'isPartOf\'}, {related_resource: isBasedOn, relation_type: \'isBasedOn\'}], ' \

    #TODO: more real life examples are needed to provide a valid mapping for microdata
    MICRODATA_MAPPING = '{object_type: type, title: properties.name, summary: properties.description, publication_date: properties.datePublished, ' \
                        'publisher: (properties.publisher.properties.name || properties.publisher),' \
                        'creator: (properties.creator.properties.name || properties.author.properties.name)' \
                        '}'

    # <rightsList><rights>
    DATACITE_JSON_MAPPING = '{object_identifier: id, object_type: types.resourceTypeGeneral,  ' \
                        'creator: creators[*].name, creator_first: creators[*].givenName,' \
                        'creator_last: creators[*].familyName, publisher: publisher, ' \
                        'contributor: contributors[*].name || contributors[*].familyName, '\
                        'right_holder: contributors[?contributorType == \'RightsHolder\'], '\
                        'title: titles[0].title, keywords: subjects[*].subject, publication_date: dates[?dateType ==\'Available\'].date || publicationYear,' \
                        'data_size:sizes[0], data_file_format: formats, license: rightsList[*].rightsUri || rightsList[*].rights ,' \
                        'summary: descriptions[?descriptionType == \'Abstract\'].description || descriptions[0].description, ' \
                        'related_resources: ( relatedIdentifiers[*].{related_resource: relatedIdentifier, relation_type:relationType, scheme_uri: schemeUri}), datacite_client: clientId, ' \
                        'modified_date: dates[?dateType == \'Updated\'].date,' \
                        'created_date: dates[?dateType == \'Created\'].date,' \
                        'accepted_date: dates[?dateType == \'Accepted\'].date,' \
                        'submitted_date: dates[?dateType == \'Submitted\'].date,' \
                        'object_content_identifier:  {url: contentUrl} , access_level: rightsList[*].rightsUri || rightsList[*].rights }'
                        #'related_resources: relatedIdentifiers[*].[relatedIdentifier,relationType]}'

    PROVENANCE_MAPPING = {'contributor':'prov:wasAttributedTo', 'creator':'prov:wasAttributedTo', 'publisher':'prov:wasAttributedTo', 'right_holder':'prov:wasAttributedTo','created_date':'prov:generatedAtTime', 'publication_date':'prov:generatedAtTime',
                          'accepted_date':'prov:generatedAtTime' ,'submitted_date':'prov:generatedAtTime' ,'modified_date':'prov:generatedAtTime',
                          'hasFormat' :'prov:alternateOf', 'isFormatOf':'prov:alternateOf','isVersionOf':'prov:wasRevisionOf','isNewVersionOf':'prov:wasRevisionOf',
                          'isReferencedBy':'prov:hadDerivation', 'isReplacedBy':'prov:wasRevisionOf', 'References': 'prov:wasDerivedFrom','IsDerivedFrom': 'prov:wasDerivedFrom',
                          'isBasedOn':'prov:hadPrimarySource','hasVersion':'prov:hadRevision','Obsoletes':'prov:wasRevisionOf','Replaces':'prov:wasDerivedFrom'}

    GENERIC_SPARQL = """
            PREFIX dct: <http://purl.org/dc/terms/>
            PREFIX dc: <http://purl.org/dc/elements/1.1/>
            SELECT  ?object_identifier ?title ?summary ?publisher ?publication_date ?creator ?object_type ?license ?access_level ?keywords ?references ?source ?isVersionOf ?isReferencedBy
            WHERE {
            OPTIONAL {?dataset  dct:title|dc:title ?title}
            OPTIONAL {?dataset dct:identifier|dc:identifier ?object_identifier}
            OPTIONAL {?dataset  dct:description|dc:description ?summary}
            OPTIONAL {?dataset  dct:publisher|dc:publisher ?publisher}
            OPTIONAL {?dataset  dct:created|dct:issued|dct:date|dc:created|dc:issued|dc:date ?publication_date}
            OPTIONAL {?dataset  dct:creator|dc:creator ?creator}
            OPTIONAL {?dataset  dct:type|dc:type ?object_type}
            OPTIONAL {?dataset  dct:license|dc:license ?license}
            OPTIONAL {?dataset  dct:accessRights|dct:rights|dc:rights ?access_level}
            OPTIONAL {?dataset  dct:subject|dc:subject ?keywords}
            OPTIONAL {?dataset  dct:references|dc:references ?references}
            OPTIONAL {?dataset  dct:isReferencedBy ?isReferencedBy}
            OPTIONAL {?dataset  dc:source|dct:source ?source}
            OPTIONAL {?dataset  dct:isVersionOf ?isVersionOf}
            }
            """
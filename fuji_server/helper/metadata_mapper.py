
from enum import Enum

class Mapper(Enum):
    ## ============================ CONFIGURATIONS ============================ ##
    # List of PIDS
    VALID_PIDS = ['doi', 'handle', 'ark', 'purl', 'lsid']

    # reference metadata elements (used by FUJI)
    #['creator','license','related_resources'] --> list type
    # datacite_client --> retrieve re3data records
    # TODO include data types of all reference elements
    REFERENCE_METADATA_LIST = ['object_identifier', 'creator', 'title', 'publisher', 'publication_date', 'summary', 'keywords',
                 'object_content_identifier', 'access_level', 'embargoe', 'access_info', 'policy','related_resources','provenance_general',
                 'measured_variable', 'method', 'creation_date', 'contributor','version', 'license','data_file_format', 'object_type', 'data_size','datacite_client']

    # core metadata elements (FsF-F2-01M)
    REQUIRED_CORE_METADATA = ['creator', 'title', 'publisher', 'publication_date', 'summary', 'keywords','object_identifier']

    ## ============================ METADATA MAPPINGS ============================ ##

    # https://www.dublincore.org/specifications/dublin-core/dcmi-terms/
    # license: Recommended practice is to identify the license document with a URI. If this is not possible or feasible, a literal value that identifies the license may be provided.
    DC_MAPPING = {'object_identifier': 'identifier', 'creator': 'creator', 'title': 'title',
              'publisher': 'publisher', 'publication_date': 'date', 'summary': 'abstract',
              'keywords': 'subject', 'object_type': 'type',
              'license': 'license', 'data_file_format': 'format'}

    # https://ogp.me/
    # og:url ->The canonical URL of your object that will be used as its permanent ID in the graph (assume this is fuji:object_indentifier)
    OG_MAPPING = {'title': 'og:title', 'object_identifier': 'og:url', 'summary': 'og:description',
              'object_type': 'og:type', 'publisher': 'og:site_name'}

    # Schema.org
    ## A license document that applies to this content, typically indicated by URL.
    SCHEMAORG_MAPPING = '{title: name, object_type: "@type", date: datePublished."@value" ||datePublished , ' \
                           'creator: creator[*].name || author[*].name || creator.name || author.name, ' \
                           'creator_first: creator[*].givenName || author[*].givenName || creator.givenName || author.givenName,' \
                           'creator_last: creator[*].familyName || author[*].familyName || creator.familyName || author.familyName,' \
                           'publisher: publisher.name, license: (license."@id" || license.license."@id") || license, ' \
                           'summary: description, keywords: keywords, publication_date: datePublished, data_file_format: encodingFormat,' \
                           'object_identifier: (identifier || "@id" || identifier.value ) || (url || url."@id") , ' \
                        'object_content_identifier: (distribution[*].{url: contentUrl, type: (encodingFormat || fileFormat), size: contentSize, profile: schemaVersion} || [distribution.{url: contentUrl, type: (encodingFormat || fileFormat), size: contentSize, profile: schemaVersion}])}'

    DATACITE_JSON_MAPPING = '{ object_identifier: id, object_type: types.resourceTypeGeneral,  ' \
                        'creator: creators[*].name, creator_first: creators[*].givenName,' \
                        'creator_last: creators[*].familyName, publisher: publisher, ' \
                        'title: titles[0].title, keywords: subjects[*].subject, publication_date: dates[?dateType ==\'Available\'].date,' \
                        'data_size:sizes[0], data_file_format: formats, license: rightsList[*].rights || rightsList[*].rightsUri,' \
                        'summary: descriptions[?descriptionType == \'Abstract\'].description || descriptions[0].description, ' \
                        'related_resources: relatedIdentifiers[*], datacite_client: clientId ' \
                        'object_content_identifier:  [{url: contentUrl}] }'
                        #'related_resources: relatedIdentifiers[*].[relationType, relatedIdentifier]}'

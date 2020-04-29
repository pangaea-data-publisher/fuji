import enum
## ============================ CONFIGURATIONS ============================ ##

# List of PIDS
VALID_PIDS = ['doi', 'handle', 'ark', 'purl', 'lsid']

# Using enum class create enumerations of metadata sources
class Sources(enum.Enum):
    DUBLINCORE = 'Embedded DublinCore'
    OPENGRAPH = 'Embedded OpenGraph'
    SCHEMAORG_EMBED = 'Schema.org JSON-LD (Embedded)'
    SCHEMAORG_NEGOTIATE = 'Schema.org JSON-LD (Datacite)'
    DATACITE_JSON = 'Datacite Metadata'
    SIGN_POSTING = 'Signposting Typed Links'

# reference metadata elements
CORE_METADATA = ['data_identifier', 'creator', 'title', 'publisher', 'publication_date', 'summary', 'keywords',
                 'data_access_url', 'access_level', 'embargoe', 'access_info', 'related_resources', 'provenance',
                 'license','data_file_format', 'type', 'data_size']

# core metadata elements (FsF-F2-01M)
REQUIRED_CORE_METADATA = ['creator', 'title', 'publisher', 'publication_date', 'summary', 'keywords']

## ============================ METADATA MAPPINGS ============================ ##

# https://www.dublincore.org/specifications/dublin-core/dcmi-terms/
# license: Recommended practice is to identify the license document with a URI. If this is not possible or feasible, a literal value that identifies the license may be provided.
DC_MAPPING = {'data_identifier': 'identifier', 'creator': 'creator', 'title': 'title',
              'publisher': 'publisher', 'publication_date': 'date', 'summary': 'abstract',
              'keywords': 'subject', 'type': 'type',
              'license': 'license', 'data_file_format': 'format'}

# https://ogp.me/
OG_MAPPING = {'title': 'og:title', 'data_identifier': 'og:url', 'summary': 'og:description',
              'type': 'og:type', 'publisher': 'og:site_name'}

# Schema.org
## A license document that applies to this content, typically indicated by URL.
SCHEMAORG_MAPPING = '{title: name, type: "@type", date: datePublished."@value" ||datePublished , ' \
                           'creator: creator[*].name || author[*].name || creator.name || author.name, ' \
                           'creator_first: creator[*].givenName || author[*].givenName || creator.givenName || author.givenName,' \
                           'creator_last: creator[*].familyName || author[*].familyName || creator.familyName || author.familyName,' \
                           'publisher: publisher.name, license: (license."@id" || license.license."@id") || license, ' \
                           'summary: description, keywords: keywords, publication_date: datePublished, data_file_format: encodingFormat,' \
                           'data_identifier: ("@id" || url."@id" || identifier.value ) || url, data_access_url: (distribution.contentUrl || distribution[*].contentUrl)}'

DATACITE_JSON_MAPPING = '{ data_identifier: id, type: types.resourceTypeGeneral,  ' \
                        'creator: creators[*].name, creator_first: creators[*].givenName,' \
                        'creator_last: creators[*].familyName, publisher: publisher, ' \
                        'title: titles[0].title, keywords: subjects[*].subject, publication_date: dates[?dateType ==\'Available\'].date,' \
                        'data_size:sizes[0], data_file_format: formats, license: rightsList[*].rights || rightsList[*].rightsUri,' \
                        'summary: descriptions[?descriptionType == \'Abstract\'].description || descriptions[0].description, ' \
                        'related_resources: relatedIdentifiers[*].[relationType, relatedIdentifier]}'


from enum import Enum

class Mapper(Enum):
    ## ============================ CONFIGURATIONS ============================ ##
    # List of PIDS e.g. those listed in datacite schema
    VALID_PIDS = ['doi', 'handle', 'ark', 'purl', 'lsid','sra','biosample','ensembl','uniprot','genome']
    #identifiers.org pattern
    #TODO: check if this is needed.. if so ..complete and add check to FAIRcheck
    IDENTIFIERS_PIDS=r'https://identifiers.org/[provider_code/]namespace:accession'

    # reference metadata elements (used by FUJI)
    #['creator','license','related_resources'] --> list type
    # datacite_client --> retrieve re3data records
    # TODO include data types of all reference elements
    REFERENCE_METADATA_LIST = ['object_identifier', 'creator', 'title', 'publisher', 'publication_date', 'summary', 'keywords',
                 'object_content_identifier', 'access_level', 'access_free','policy','related_resources','provenance_general',
                 'measured_variable', 'method', 'creation_date', 'contributor','version', 'license','data_file_format', 'file_format_only',
                 'object_type', 'data_size','datacite_client', 'modified_date','created_date','right_holder', 'object_size']

    # core metadata elements (FsF-F2-01M)
    REQUIRED_CORE_METADATA = ['creator', 'title', 'publisher', 'publication_date', 'summary', 'keywords','object_identifier']


    ## ============================ METADATA MAPPINGS ============================ ##
    #https://www.dublincore.org/webinars/2015/openaire_guidelines_promoting_repositories_interoperability_and_supporting_open_access_funder_mandates/slides.pdf
    ACCESS_RIGHT_CODES = {'creativecommons': 'public', 'creative commons': 'public',
                    'c_abf2': 'public', 'c_f1cf': 'embargoed', 'c_16ec': 'restricted', 'c_14cb': 'metadata_only',
                    'OpenAccess': 'public', 'ClosedAccess': 'closed_metadataonly', 'RestrictedAccess': 'restricted',
                    'NON_PUBLIC': 'restricted', 'OP_DATPRO': 'embargoed', 'PUBLIC': 'public',
                    'RESTRICTED': 'restricted', 'SENSITIVE': 'embargoed'
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
                            'publication_date: datePublished."@value" || datePublished , '\
                            'modified_date: dateModified."@value" ||dateModified, ' \
                           'creator: creator[?"@type" ==\'Person\'].name || author[*].name || creator.name || author.name, ' \
                           'creator_first: creator[*].givenName || author[*].givenName || creator.givenName || author.givenName,' \
                           'creator_last: creator[*].familyName || author[*].familyName || creator.familyName || author.familyName,' \
                           'contributor: contributor[*].name || contributor[*].familyName, ' \
                           'right_holder: copyrightHolder[*].name || copyrightHolder[*].familyName, ' \
                           'publisher: publisher.name, license: (license."@id" || license[*].id || license[*].url || license[*].name) || license, ' \
                           'summary: description, keywords: keywords, ' \
                           'object_identifier: (identifier.value || identifier[0].value || identifier || "@id") || (url || url."@id") , ' \
                            'access_level: conditionsOfAccess, ' \
                            'access_free:  (isAccessibleForFree || free), ' \
                            'measured_variable: variableMeasured[*].name || variableMeasured , object_size: size,' \
                            'related_resources: [{related_resource: isPartOf."@id" || isPartOf.url || isPartOf, relation_type: \'isPartOf\'}, {related_resource: "@reverse".isBasedOn."@id" || "@reverse".isBasedOn.url || isBasedOn , relation_type: \'isBasedOn\'} ], ' \
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
                        'related_resources: relatedIdentifiers[*], datacite_client: clientId, ' \
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
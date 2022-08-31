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

from enum import Enum


class Mapper(Enum):
    """
    Enum class to Map metadata into reference metadata list, access right code, provenance,
    and metadata sources, e.g., Dublin Core, Open Graph, Microdata, Datacite, ORE Atom, Schema.org, etc.
    """
    ## ============================ CONFIGURATIONS ============================ ##
    # List of PIDS e.g. those listed in datacite schema
    VALID_PIDS = [
        'ark', 'arxiv', 'bioproject', 'biosample', 'doi', 'ensembl', 'genome', 'gnd', 'handle', 'lsid', 'pmid', 'pmcid',
        'purl', 'refseq', 'sra', 'uniprot', 'urn','identifiers.org','w3id'
    ]

    #identifiers.org pattern
    #TODO: check if this is needed.. if so ..complete and add check to FAIRcheck
    IDENTIFIERS_PIDS = r'https://identifiers.org/[provider_code/]namespace:accession'

    #CMMI capability maturity levels
    MATURITY_LEVELS = {0: 'incomplete', 1: 'initial', 2: 'moderate', 3: 'advanced'}

    # reference metadata elements (used by FUJI)
    #['creator','license','related_resources'] --> list type
    # datacite_client --> retrieve re3data records
    # TODO include data types of all reference elements
    REFERENCE_METADATA_LIST = [
        'object_identifier', 'creator', 'title', 'publisher', 'publication_date', 'summary', 'keywords',
        'object_content_identifier', 'access_level', 'access_free', 'policy', 'related_resources', 'provenance_general',
        'measured_variable', 'method', 'creation_date', 'contributor', 'version', 'license', 'data_file_format',
        'file_format_only', 'object_type', 'data_size', 'datacite_client', 'modified_date', 'created_date',
        'right_holder', 'object_size'
    ]

    # core metadata elements (FsF-F2-01M)
    REQUIRED_CORE_METADATA = [
        'creator', 'title', 'publisher', 'publication_date', 'summary', 'keywords', 'object_identifier', 'object_type'
    ]

    ## ============================ METADATA MAPPINGS ============================ ##
    #https://www.dublincore.org/webinars/2015/openaire_guidelines_promoting_repositories_interoperability_and_supporting_open_access_funder_mandates/slides.pdf
    ACCESS_RIGHT_CODES = {
        'creativecommons': 'public',
        'creative commons': 'public',
        'c_abf2': 'public',
        'c_f1cf': 'embargoed',
        'c_16ec': 'restricted',
        'c_14cb': 'metadataonly',
        'OpenAccess': 'public',
        'ClosedAccess': 'closed',
        'RestrictedAccess': 'restricted',
        'NON_PUBLIC': 'restricted',
        'OP_DATPRO': 'embargoed',
        'PUBLIC': 'public',
        'RESTRICTED': 'restricted',
        'SENSITIVE': 'restricted',
        'embargoedAccess': 'embargoed'
    }

    #https://en.wikipedia.org/wiki/List_of_archive_formats#cite_ref-MIME_type_2-3
    # only consider mime types registered with IANA: https://www.iana.org/assignments/media-types/media-types.xhtml
    ARCHIVE_COMPRESS_MIMETYPES = [
        'application/gzip', 'application/zstd', 'application/octet-stream', 'application/vnd.ms-cab-compressed',
        'application/zip', 'application/x-gzip'
    ]

    # https://www.dublincore.org/specifications/dublin-core/dcmi-terms/
    # dc: rights, dcterm: accessRights, rightsHolder?
    # license: Recommended practice is to identify the license document with a URI. If this is not possible or feasible, a literal value that identifies the license may be provided.
    DC_MAPPING = {
        'object_identifier':
        'identifier',
        'creator':
        'creator',
        'title':
        'title',
        'contributor':
        'contributor',
        'publisher':
        'publisher',
        'publication_date': ['date', 'available', 'issued'],
        'summary': ['abstract', 'description'],
        'keywords':
        'subject',
        'object_type':
        'type',
        'modified_date':
        'modified',
        'created_date':
        'created',
        'license':
        'license',
        'file_format_only':
        'format',
        'access_level': ['rights', 'accessRights'],
        'date_available':
        'available',
        'provenance_general':
        'provenance',
        'related_resources': [
            'relation', 'source', 'references', 'hasVersion', 'isReferencedBy', 'isVersionOf', 'hasVersion', 'replaces',
            'requires', 'conformsTo', 'hasFormat', 'hasPart', 'isPartOf', 'isReplacedBy', 'isRequiredBy'
        ]
    }

    # https://ogp.me/
    # og:url ->The canonical URL of your object that will be used as its permanent ID in the graph (assume this is fuji:object_indentifier)
    OG_MAPPING = {
        'title': 'og:title',
        'object_identifier': 'og:url',
        'summary': 'og:description',
        'object_type': 'og:type',
        'publisher': 'og:site_name'
    }

    # Schema.org
    # conditionsOfAccess, usageInfo?, isAccessibleForFree
    ## A license document that applies to this content, typically indicated by URL.
    SCHEMAORG_MAPPING = '{title: name[*]."@value" || name, object_type: "@type", '\
                            'publication_date: datePublished."@value" || datePublished || dateCreated, '\
                            'modified_date: dateModified."@value" ||dateModified, ' \
                           'creator: creator[?"@type" ==\'Person\'].name || creator[?"@type" ==\'Organization\'].name || author[*].name || creator.name || author.name, ' \
                           'creator_first: creator[*].givenName || author[*].givenName || creator.givenName || author.givenName,' \
                           'creator_last: creator[*].familyName || author[*].familyName || creator.familyName || author.familyName,' \
                           'contributor: contributor[*].name || contributor[*].familyName, ' \
                           'right_holder: copyrightHolder[*].name || copyrightHolder[*].familyName, ' \
                           'publisher: publisher.name || provider.name || publisher || provider, ' \
                           'license: license."@id" || license[?"@type" ==\'CreativeWork\'].id || license[?"@type" ==\'CreativeWork\'].url || license[?"@type" ==\'CreativeWork\'].name || license, ' \
                           'summary: description, keywords: keywords, ' \
                           'object_identifier: (identifier.value || identifier[0].value || identifier || "@id") || (url || url."@id") , ' \
                            'access_level: conditionsOfAccess, ' \
                            'access_free:  (isAccessibleForFree || free), ' \
                            'measured_variable: variableMeasured[*].name || variableMeasured , object_size: size,' \
                            'related_resources: [{related_resource: (isPartOf."@id" || isPartOf[0]."@id" || isPartOf.url || isPartOf[0].url || isPartOf), relation_type: \'isPartOf\'}, ' \
                            '{related_resource: (sameAs."@id" || sameAs[0]."@id" || sameAs.url || sameAs[0].url || sameAs), relation_type: \'sameAs\'},' \
                            '{related_resource: (includedInDataCatalog."@id" || includedInDataCatalog[0]."@id" || includedInDataCatalog.url || includedInDataCatalog[0].url || includedInDataCatalog.name || includedInDataCatalog[0].name || includedInDataCatalog), relation_type: \'isPartOf\'}, ' \
                            '{related_resource: (subjectOf."@id" || subjectOf[0]."@id" || subjectOf.url ||subjectOf[0].url || subjectOf.name || subjectOf[0].name || subjectOf), relation_type: \'isReferencedBy\'},' \
                            '{related_resource: (isBasedOn."@id" || isBasedOn[0]."@id" || isBasedOn.url || isBasedOn[0].url || isBasedOn) , relation_type: \'isBasedOn\'} , ' \
                            '{related_resource: "@reverse".isBasedOn[0]."@id" || "@reverse".isBasedOn."@id" || "@reverse".isBasedOn[0].url || isBasedOn , relation_type: \'isBasisFor\'} ], ' \
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

    PROVENANCE_MAPPING = {
        'contributor': 'prov:wasAttributedTo',
        'creator': 'prov:wasAttributedTo',
        'publisher': 'prov:wasAttributedTo',
        'right_holder': 'prov:wasAttributedTo',
        'created_date': 'prov:generatedAtTime',
        'publication_date': 'prov:generatedAtTime',
        'accepted_date': 'prov:generatedAtTime',
        'submitted_date': 'prov:generatedAtTime',
        'modified_date': 'prov:generatedAtTime',
        'hasFormat': 'prov:alternateOf',
        'isFormatOf': 'prov:alternateOf',
        'isVersionOf': 'prov:wasRevisionOf',
        'isNewVersionOf': 'prov:wasRevisionOf',
        'isReferencedBy': 'prov:hadDerivation',
        'isReplacedBy': 'prov:wasRevisionOf',
        'References': 'prov:wasDerivedFrom',
        'IsDerivedFrom': 'prov:wasDerivedFrom',
        'isBasedOn': 'prov:hadPrimarySource',
        'hasVersion': 'prov:hadRevision',
        'Obsoletes': 'prov:wasRevisionOf',
        'Replaces': 'prov:wasDerivedFrom'
    }

    GENERIC_SPARQL = """
            PREFIX dct: <http://purl.org/dc/terms/>
            PREFIX dc: <http://purl.org/dc/elements/1.1/>
            PREFIX sdo: <http://schema.org/>
            SELECT  ?object_identifier ?title ?summary ?publisher ?publication_date ?creator ?object_type ?license ?access_level ?keywords ?references ?source ?isVersionOf ?isReferencedBy ?isPartOf ?hasVersion ?replaces ?hasPart ?isReplacedBy ?requires ?isRequiredBy
            WHERE {
            OPTIONAL {?dataset  dct:title|dc:title|sdo:name ?title}
            OPTIONAL {?dataset dct:identifier|dc:identifier|sdo:identifier ?object_identifier}
            OPTIONAL {?dataset  dct:description|dc:description|sdo:abstract ?summary}
            OPTIONAL {?dataset  dct:publisher|dc:publisher|sdo:publisher ?publisher}
            OPTIONAL {?dataset  dct:created|dct:issued|dct:date|dc:created|dc:issued|dc:date|sdo:dateCreated|sdo:datePublished ?publication_date}
            OPTIONAL {?dataset  dct:creator|dc:creator|sdo:author ?creator}
            OPTIONAL {?dataset  dct:type|dc:type ?object_type}
            OPTIONAL {?dataset  dct:license|dc:license|sdo:license ?license}
            OPTIONAL {?dataset  dct:accessRights|dct:rights|dc:rights ?access_level}
            OPTIONAL {?dataset  dct:subject|dc:subject|sdo:keywords ?keywords}
            OPTIONAL {?dataset  dct:references|dc:references ?references}
            OPTIONAL {?dataset  dct:isReferencedBy ?isReferencedBy}
            OPTIONAL {?dataset  dc:source|dct:source ?source}
            OPTIONAL {?dataset  dct:isVersionOf ?isVersionOf}
            OPTIONAL {?dataset  dct:isPartOf|sdo:isPartOf ?isPartOf}
            OPTIONAL {?dataset  dct:hasVersion ?hasVersion}
            OPTIONAL {?dataset  dct:replaces ?replaces}
            OPTIONAL {?dataset  dct:hasPart ?hasPart}
            OPTIONAL {?dataset  dct:requires ?requires}
            OPTIONAL {?dataset  dct:isRequiredBy ?isRequiredBy}            
            }LIMIT 1
            """

    #################  XML Mappings ###############
    # relations: indicate type using: related_resource_[opional relation type] alternative: define a list 'related_resource_type'
    # content identifiers: object_content_identifier_url, object_content_identifier_size, object_content_identifier_type (should have same length)
    # attributes: must be indicated like this: tag@@attribute

    XML_MAPPING_DUBLIN_CORE = {
        'title': {
            'path': './{*}title'
        },
        'creator': {
            'path': './{*}creator'
        },
        'contributor': {
            'path': './{*}contributor'
        },
        'keywords': {
            'path': './{*}subject'
        },
        'summary': {
            'path': './{*}description'
        },
        'publisher': {
            'path': './{*}publisher'
        },
        'keywords': {
            'path': './{*}subject'
        },
        'publication_date': {
            'path': ['./{*}date', './{*}available', './{*}issued']
        },
        'created_date': {
            'path': './{*}created'
        },
        'object_identifier': {
            'path': './{*}identifier'
        },
        'related_resource': {
            'path': [
                './{*}related', './{*}source', './{*}references', './{*}hasVersion', './{*}isReferencedBy',
                './{*}isVersionOf', './{*}hasVersion', './{*}replaces', './{*}requires', './{*}conformsTo',
                './{*}hasFormat', './{*}hasPart', './{*}isPartOf', './{*}isReplacedBy', './{*}isRequiredBy'
            ]
        },
        'license': {
            'path': './{*}license'
        },
        'access_level': {
            'path': ['./{*}rights', './{*}accessRights']
        },
        'object_type': {
            'path': './{*}type'
        },
        'provenance_general': {
            'path': './{*}provenance'
        }
    }

    XML_MAPPING_DATACITE = {
        'title': {
            'path': './{*}titles/{*}title'
        },
        'creator': {
            'path': './{*}creators/{*}creator/{*}creatorName'
        },
        'contributor': {
            'path': './{*}contributors/{*}contributorName'
        },
        'publication_date': {
            'path': './{*}publicationYear'
        },
        'keywords': {
            'path': './{*}subjects/{*}subject'
        },
        'object_identifier': {
            'path': './{*}identifier'
        },
        'publisher': {
            'path': './{*}publisher'
        },
        'summary': {
            'path': './{*}descriptions/{*}description'
        },
        'object_type': {
            'path': './{*}resourceType@@resourceTypeGeneral'
        },
        'related_resource': {
            'path': './{*}relatedIdentifiers/{*}relatedIdentifier'
        },
        'related_resource_type': {
            'path': './{*}relatedIdentifiers/{*}relatedIdentifier@@relationType'
        },
        'license': {
            'path': ['./{*}rightsList/{*}rights', './{*}rightsList/{*}rights@@rightsURI']
        },
        'access_level': {
            'path': ['./{*}rightsList/{*}rights', './{*}rightsList/{*}rights@@rightsURI']
        }
    }

    XML_MAPPING_METS = {
        'publisher': {
            'path': './{*}metsHdr/{*}agent[@ROLE="CREATOR"]/{*}name'
        },
        'object_content_identifier_url': {
            'path': './{*}fileSec/{*}fileGrp/{*}file/{*}FLocat@@xlink:href'
        },
        'object_content_identifier_type': {
            'path': './{*}fileSec/{*}fileGrp/{*}file@@MIMETYPE'
        }
    }

    XML_MAPPING_MODS = {
        'title': {
            'path': './{*}titleInfo/{*}title'
        },
        'creator': {
            'path': [
                "./{*}name/{*}role[{*}roleTerm='Creator']/../{*}namePart[1]",
                "./{*}name/{*}role[{*}roleTerm='Author']/../{*}namePart[1]"
            ]
        },
        'publisher': {
            'path': './{*}originInfo/{*}publisher'
        },
        'object_identifier': {
            'path': './{*}identifier'
        },
        'publication_date': {
            'path': './{*}originInfo/{*}dateCreated'
        },
        'related_resource': {
            'path': ['./{*}relatedItem/{*}recordInfo/{*}recordIdentifier', './{*}relatedItem/{*}identifier']
        },
        'related_resource_type': {
            'path': ['./{*}relatedItem@@type', './{*}relatedItem@@type']
        },
        'keywords': {
            'path': './{*}subject/{*}topic'
        },
        'summary': {
            'path': './{*}abstract'
        },
        'object_type': {
            'path': './{*}typeOfResource'
        },
        'access_level': {
            'path': ['./{*}accessCondition', './{*}accessCondition@@type', './{*}accessCondition@@href']
        },
        'license': {
            'path': ['./{*}accessCondition', './{*}accessCondition@@type', './{*}accessCondition@@href']
        }
    }

    XML_MAPPING_EML = {
        'title': {
            'path': './{*}dataset/{*}title'
        },
        'object_identifier': {
            'path': ['./{*}dataset/{*}alternateIdentifier', './/@@packageId']
        },
        'creator': {
            'path': './{*}dataset/{*}individualName/{*}surName'
        },
        'contributor': {
            'path': './{*}dataset/{*}associatedParty/{*}surName'
        },
        'publication_date': {
            'path': './{*}dataset/{*}pubDate'
        },
        'keywords': {
            'path': './{*}dataset/{*}keywordSet/{*}keyword'
        },
        'summary': {
            'path': './{*}dataset/{*}abstract/{*}para'
        },
        'publisher': {
            'path': './{*}dataset/{*}publisher/{*}organizationName'
        },
        'measured_variable': {
            'path': './/{*}additionalMetadata/{*}metadata/{*}variableName'
        },
        'license': {
            'path': [
                './{*}dataset/{*}intellectualRights/{*}para',
                '{*}dataset/{*}intellectualRights/{*}section/{*}para/{*}value'
            ]
        },
        'object_content_identifier_url': {
            'path': [
                './{*}dataset/{*}dataTable/{*}physical/{*}distribution/{*}online/{*}url',
                './/{*}dataset/{*}distribution/{*}online/{*}url'
            ]
        },
        'object_content_identifier_size': {
            'path': './{*}dataset/{*}dataTable/{*}physical/{*}distribution/{*}online/{*}size'
        }
    }
    XML_MAPPING_CMD ={
        'object_identifier': {
            'path': './{*}Header/{*}MdSelfLink'
        },
        'creator': {
            'path': './{*}Header/{*}MdCreator'
        },
        'publication_date': {
            'path': './{*}Header/{*}MdCreationDate'
        },
        'publisher': {
            'path': './{*}Header/{*}MdCollectionDisplayName'
        },
        'object_content_identifier_url': {
            'path':'./{*}Resources/{*}ResourceProxyList/{*}ResourceProxy/{*}ResourceRef'
        },
        'object_content_identifier_type': {
            'path': './{*}Resources/{*}ResourceProxyList/{*}ResourceProxy/{*}ResourceType@@mimetype'
        }
    }
    '''
    local standard? dda.dk/metadata/1.0.0 see: http://dda.dk/search-technical-information/schema/MetaDataSchema.xsd
    XML_MAPPING_DDA_DK_STUDY ={
        'object_identifier': {
            'path': './{*}PIDs/{*}PID/{*}ID'
        },
        'title': {
            'path': './{*}Titles/{*}Title'
        },
        'creator':{
            'path': './{*}PrincipalInvestigators/{*}PrincipalInvestigator'
        },
        'publication_date': {
            'path': './{*}StudyPublicationDate'
        },
        'access_level': {
            'path':'./{*}Access/{*}Condition'
        },
        'publisher': {
            'path': './{*}Archive'
        },
        'summary': {
            'path':"./{*}StudyDescriptions/{*}StudyDescription[{*}Type='Abstract']"
        },
        'keywords': {
            'path':['./{*}TopicalCoverage/{*}Subjects/{*}Subject', './{*}TopicalCoverage/{*}Keywords/{*}Keyword']
        }

    }
    '''
    XML_MAPPING_DDI_STUDYUNIT = {
        'title':{
            'path':'./{*}Citation/{*}Title'
        },'creator': {
            'path': './{*}Citation/{*}Creator'
        },
        'object_identifier':{
            'path':'./{*}Citation/{*}InternationalIdentifier'
        },
        'publisher': {
            'path':'./{*}Citation/{*}Publisher'
        },
        'publication_date': {
            'path':'./{*}Citation/{*}PublicationDate'
        },
        'summary': {
            'path': './{*}Abstract'
        },
        'keywords': {
            'path':'./{*}Coverage/{*}TopicalCoverage/{*}Subject'
        },
        'access_level': {
            'path':'.//{*}AccessConditions'
        },
        'related_resource':{
            'path':'./{*}RelatedOtherMaterialReference'
        },
        'related_resource_hasVersion': {
            'path': './{*}Version'
        },
        'related_resource_isBasedOn': {
            'path':'./{*}BasedOnObject'
        },
        'measured_variable': {
            'path': './{*}LogicalProduct/{*}VariableScheme/{*}Variable/{*}Label'
        }
    }

    XML_MAPPING_DDI_CODEBOOK = {
        'title': {
            'path': './{*}stdyDscr/{*}citation/{*}titlStmt/{*}titl'
        },
        'creator': {
            'path': './{*}stdyDscr/{*}citation/{*}rspStmt/{*}AuthEnty'
        },
        'keywords': {
            'path':
            ['./{*}stdyDscr/{*}stdyInfo/{*}subject/{*}keyword', './{*}stdyDscr/{*}stdyInfo/{*}subject/{*}topcClas']
        },
        'summary': {
            'path': './{*}stdyDscr/{*}stdyInfo/{*}abstract'
        },
        'publisher': {
            'path':
            ['./{*}docDscr/{*}citation/{*}prodStmt/{*}producer', './{*}stdyDscr/{*}citation/{*}distStmt/{*}distrbtr']
        },
        'publication_date': {
            'path': './{*}docDscr/{*}citation/{*}prodStmt/{*}prodDate@@date'
        },
        'object_identifier': {
            'path': [
                './{*}stdyDscr/{*}dataAccs/{*}setAvail/{*}accsPlac@@URI',
                './{*}docDscr/{*}citation/{*}titlStmt/{*}IDNo', './{*}docDscr/{*}citation/{*}holdings@@URI',
                './{*}stdyDscr/{*}citation/{*}titlStmt/{*}IDNo'
            ]
        },
        'related_resource': {
            'path': ['./{*}stdyDscr/{*}method/{*}dataColl/{*}sources', './{*}stdyDscr/{*}othrStdyMat/*']
        },
        'related_resource_hasVersion': {
            'path': ['./{*}docDscr/{*}citation/{*}verStmt', './{*}stdyDscr/{*}citation/{*}verStmt']
        },
        'related_resource_isPartOf': {
            'path':
            ['./{*}docDscr/{*}citation/{*}serStmt/{*}serName', './{*}stdyDscr/{*}citation/{*}serStmt/{*}serName']
        },
        'license': {
            'path':
            ['./{*}docDscr/{*}citation/{*}prodStmt/{*}copyright', './{*}stdyDscr/{*}citation/{*}prodStmt/{*}copyright']
        },
        'object_type': {
            'path': './{*}stdyDscr/{*}stdyInfo/{*}sumDscr/{*}dataKind'
        },
        'access_level': {
            'path': ['./{*}stdyDscr/{*}dataAccs/{*}setAvail/{*}avlStatus', './{*}stdyDscr/{*}dataAccs/{*}useStmt/*']
        },
        'object_content_identifier_url': {
            'path': './/{*}fileDscr@@URI'
        },
        'measured_variable': {
            'path': './{*}dataDscr/{*}var@@name'
        }
    }
    XML_MAPPING_DIF ={
        'object_identifier':{
            'path':'./{*}Dataset_Citation/{*}Persistent_Identifier'
        },
        'title': {
            'path':'./{*}Dataset_Citation/{*}Dataset_Title'
        },
        'publication_date': {
            'path':'./{*}Dataset_Citation/{*}Dataset_Release_Date'
        },
        'creator': {
            'path': './{*}Dataset_Citation/{*}Dataset_Creator'
        },
        'summary': {
            'path': './{*}Summary/{*}Abstract'
        },
        'publisher': {
            'path':['./{*}Dataset_Citation/{*}Dataset_Publisher','./{*}Data_Center/{*}Data_Center_Name']
        },
        'keywords': {
            'path':['./{*}Science_Keywords/{*}Category','./{*}Science_Keywords/{*}Topic','./{*}Science_Keywords/{*}Term']
        },
        'object_content_identifier_url': {
            'path':'./{*}Distribution/{*}Distribution_Media'
        },
        'object_content_identifier_size': {
            'path': './{*}Distribution/{*}Distribution_Size'
        },
        'object_content_identifier_type': {
            'path': './{*}Distribution/{*}Distribution_Format'
        },
        'measured_variable': {
            'path':'./{*}Science_Keywords/{*}Detailed_Variable'
        },
        'access_level': {
            'path': ['./{*}Access_Constraints','./{*}Use_Constraints']
        },
        'related_resource': {
            'path':'./{*}Related_URL/{*}URL'
        },
        'related_resource_type':{
            'path': './{*}Related_URL/{*}Type'
        },
        'related_resource_hasVersion': {
            'path': './{*}Dataset_Citation/{*}Version'
        }
    }
    XML_MAPPING_GCMD_ISO = {
        'title': {
            'path': [
                './{*}identificationInfo//{*}citation/{*}CI_Citation/{*}title/{*}CharacterString',
                './{*}identificationInfo//{*}citation/{*}CI_Citation/{*}title'
            ]
        },
        'publication_date': {
            'path': [
                './{*}identificationInfo//{*}citation/{*}CI_Citation/{*}date/{*}CI_Date/{*}date/{*}DateTime',
                './{*}identificationInfo//{*}citation/{*}CI_Citation/{*}date/{*}CI_Date/{*}date'
            ]
        },
        'object_identifier': {
            'path': [
                './{*}identificationInfo//{*}citation/{*}CI_Citation/{*}identifier/{*}MD_Identifier/{*}code/{*}CharacterString',
                './{*}dataSetURI/{*}CharacterString'
            ]
        },
        'creator': {
            'path': [
                './{*}identificationInfo//{*}citation/{*}CI_Citation/{*}citedResponsibleParty/{*}CI_ResponsibleParty/{*}individualName/{*}CharacterString',
                './{*}identificationInfo//{*}citation/{*}CI_Citation/{*}citedResponsibleParty/{*}CI_ResponsibleParty/{*}individualName/',
                './{*}identificationInfo//{*}pointOfContact/{*}CI_Responsibility//{*}CI_RoleCode[@codeListValue=\'pointOfContact\']/../../{*}party//{*}name',
                './{*}identificationInfo//{*}pointOfContact/{*}CI_Responsibility//{*}CI_RoleCode[@codeListValue=\'author\']/../../{*}party//{*}name'
            ]
        },
        'summary': {
            'path': './{*}identificationInfo//{*}abstract'
        },
        'keywords': {
            'path': [
                './{*}identificationInfo//{*}descriptiveKeywords/{*}MD_Keywords/{*}keyword/{*}CharacterString',
                './{*}identificationInfo//{*}topicCategory/{*}MD_TopicCategoryCode',
                './{*}identificationInfo//{*}descriptiveKeywords/{*}MD_Keywords/{*}keyword'
            ]
        },
        'publisher': {
            'path': [
                "./{*}contact/{*}CI_ResponsibleParty/{*}role[{*}CI_RoleCode='pointOfContact']/../{*}organisationName/{*}CharacterString",
                './{*}identificationInfo//{*}pointOfContact/{*}CI_Responsibility//{*}CI_RoleCode[@codeListValue=\'custodian\']/../../{*}party//{*}name',
                './{*}identificationInfo//{*}pointOfContact/{*}CI_Responsibility//{*}CI_RoleCode[@codeListValue=\'publisher\']/../../{*}party//{*}name'
            ]
        },
        'object_type': {
            'path': [
                './{*}hierarchyLevel/{*}MD_ScopeCode',
                './{*}identificationInfo//{*}spatialRepresentationType/{*}MD_SpatialRepresentationTypeCode'
            ]
        },
        'object_content_identifier_url': {
            'path': [
                './{*}distributionInfo/{*}MD_Distribution/{*}transferOptions/{*}MD_DigitalTransferOptions/{*}onLine/{*}CI_OnlineResource/{*}linkage/{*}URL',
                './{*}distributionInfo/{*}MD_Distribution//{*}CI_OnlineResource/{*}linkage/{*}URL'
            ]
        },
        'measured_variable': {
            'path': [
                './{*}contentInfo/{*}MD_CoverageDescription/{*}attributeDescription/{*}RecordType',
                #https://wiki.esipfed.org/Documenting_Resource_Content
                './{*}contentInfo/{*}MD_CoverageDescription/{*}dimension/{*}MD_Band/{*}sequenceIdentifier/{*}MemberName/{*}aName',
                './{*}contentInfo/{*}MD_CoverageDescription/{*}attributeGroup/{*}MD_AttributeGroup/{*}attribute/{*}MD_SampleDimension/{*}sequenceIdentifier/{*}MemberName/{*}aName'
            ]
        },
        'access_level': {
            'path': [
                './{*}identificationInfo//{*}resourceConstraints/{*}MD_LegalConstraints/{*}accessConstraints/{*}MD_RestrictionCode',
                './{*}identificationInfo//{*}resourceConstraints/{*}MD_LegalConstraints/{*}accessConstraints/{*}MD_RestrictionCode@@codeListValue'
            ]
        },
        'license': {
            'path': [
                './{*}identificationInfo//{*}resourceConstraints/{*}MD_LegalConstraints/{*}useConstraints/{*}MD_RestrictionCode[@codeListValue=\'license\']',
                #'./{*}identificationInfo//{*}resourceConstraints/{*}MD_LegalConstraints/{*}useConstraints/{*}MD_RestrictionCode@@codeListValue',
                './{*}identificationInfo//{*}resourceConstraints/{*}otherConstraints/{*}CharacterString',
                './{*}identificationInfo//{*}resourceConstraints/{*}MD_LegalConstraints/{*}otherConstraints/{*}Anchor',
                './{*}identificationInfo//{*}resourceConstraints/{*}MD_LegalConstraints/{*}otherConstraints/{*}Anchor@@xlink:href'
            ]
        },
        'related_resource': {
            'path': [
                './{*}identificationInfo//{*}aggregationInfo/{*}MD_AggregateInformation//{*}aggregateDataSetIdentifier/*',
                './{*}identificationInfo//{*}aggregationInfo/{*}MD_AggregateInformation//{*}aggregateDataSetName/*'
            ]
        },
        'related_resource_type': {
            'path': [
                './{*}identificationInfo//{*}aggregationInfo/{*}MD_AggregateInformation/{*}associationType/{*}DS_AssociationTypeCode@@codeListValue',
                './{*}identificationInfo//{*}aggregationInfo/{*}MD_AggregateInformation/{*}associationType/{*}DS_AssociationTypeCode@@codeListValue'
            ]
        }
    }

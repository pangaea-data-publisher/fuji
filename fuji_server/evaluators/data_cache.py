from fuji_server.helper.metadata_mapper import Mapper


class DataCache:
    oaipmh_endpoint = None
    pid_url = None  # full pid # e.g., "https://doi.org/10.1594/pangaea.906092 or url (non-pid)
    landing_url = None  # url of the landing page of self.pid_url
    landing_html = None
    landing_origin = None  # schema + authority of the landing page e.g. https://www.pangaea.de
    pid_scheme = None
    metadata_sources = []
    isMetadataAccessible = None
    metadata_merged = {}
    content_identifier = []
    community_standards = []
    community_standards_uri = {}
    namespace_uri = []
    reference_elements = Mapper.REFERENCE_METADATA_LIST.value.copy()  # all metadata elements required for FUJI metrics
    related_resources = []
    # self.test_data_content_text = None# a helper to check metadata against content
    rdf_graph = None
    sparql_endpoint = None
    rdf_collector = None

    def __init__(self, id):
        self.id = id
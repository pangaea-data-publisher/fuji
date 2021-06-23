
class RepositoryHarvester:
    def __init__(self, harvester_type ='oai', endpoint_url=''):
        self.type = harvester_type
        self.url = endpoint_url
        return True

    def identify(self):
        return True

    def harvest(self, max_records):
        self.harvested_records = []
        return True

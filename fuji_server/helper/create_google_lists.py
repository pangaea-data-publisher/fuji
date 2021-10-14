# -*- coding: utf-8 -*-
from fuji_server.helper.catalogue_helper_google_datasearch import MetaDataCatalogueGoogleDataSearch

g = MetaDataCatalogueGoogleDataSearch()

# Step 1 visit: https://www.kaggle.com/googleai/dataset-search-metadata-for-datasets
# Step 2 download the latest Dataset Search corpus file
# Step 3 indicate the location of the file below
google_file_location = ''

# Step 4 run the script
print('Starting to create Google Dataset Search files')
g.create_lists(google_file_location)
print('Finished...')

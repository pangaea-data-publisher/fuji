from fuji_server.helper.catalogue_helper_google_datasearch import MetaDataCatalogueGoogleDataSearch

g = MetaDataCatalogueGoogleDataSearch()

# Step 1 visit: https://www.kaggle.com/googleai/dataset-search-metadata-for-datasets
# Step 2 download the latest Dataset Search corpus file
# Step 3 indicate the location of the file below
google_file_location = None

# Step 4 run the script
if google_file_location is None:
    # Throw an exception instead?
    # pass # do not be verbose otherwise this gets printed on import
    print("Could not create Google Dataset Search files, no google_file_location specified, please do so.")
else:
    print("Starting to create Google Dataset Search files")
    g.create_lists(google_file_location)
    print("Finished...")

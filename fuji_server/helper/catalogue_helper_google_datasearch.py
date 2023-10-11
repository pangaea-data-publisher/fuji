import logging
import os
import re
import sqlite3 as sl
from random import randint
from time import sleep

import pandas as pd
import requests
from bs4 import BeautifulSoup

from fuji_server.helper.catalogue_helper import MetaDataCatalogue
from fuji_server.helper.preprocessor import Preprocessor


class MetaDataCatalogueGoogleDataSearch(MetaDataCatalogue):
    """A class to access Google Data Search metadata catalogue
    Attributes
    ----------
    isListed : bool, optional
        Boolean to check whether the metadata is listed in the metadata catalog,
        default is False

    Methods
    -------
    query(pid)
        Method to check whether the metadata given by PID is listed in Google Data Search
    create_list(google_cache_file)
    create_cache_db(google_cache_file)
    random_sample(limit)

    """

    islisted = False

    # apiURI = 'https://api.datacite.org/dois'
    def __init__(self, logger: logging.Logger = None, object_type=None):
        self.logger = logger
        self.source = self.getEnumSourceNames().GOOGLE_DATASET.value
        self.google_cache_db_path = os.path.join(Preprocessor.fuji_server_dir, "data", "google_cache.db")

        self.google_custom_search_id = Preprocessor.google_custom_search_id
        self.google_custom_search_api_key = Preprocessor.google_custom_search_api_key
        self.object_type = object_type

    def random_sample(self, limit):
        sample = []
        try:
            con = sl.connect(self.google_cache_db_path)
            with con:
                samplef = pd.read_sql_query("SELECT uri FROM google_links ORDER BY RANDOM() LIMIT " + str(limit), con)
                sample = samplef["uri"].values.tolist()
        except Exception as e:
            print(e)
        return sample

    def query(self, pidlist):
        # print(sys.getsizeof(Preprocessor.google_data_dois))
        pidlist = [p for p in pidlist if p is not None]
        response = None
        found_google_links = None
        if not os.path.exists(self.google_cache_db_path):
            self.logger.warning(
                "FsF-F4-01M : Google Search Cache DB does not exist, see F-UJI installation instructions"
            )
        else:
            try:
                con = sl.connect(self.google_cache_db_path)
                with con:
                    dbquery = (
                        "SELECT LOWER(uri) FROM google_links where uri IN("
                        + ", ".join(f"'{str(pid).lower()}'" for pid in pidlist)
                        + ")"
                    )

                    dbres = con.execute(dbquery)
                    found_google_links = dbres.fetchall()
            except Exception as e:
                self.logger.warning("FsF-F4-01M : Google Search Cache DB Query Error: -:" + str(e))

        if found_google_links:
            self.islisted = True
        elif self.google_custom_search_id and self.google_custom_search_api_key:
            for url_to_test in pidlist:
                found_at_google = self.query_google_custom_search(url_to_test, pidlist)
                if found_at_google:
                    self.islisted = True
                    break
        else:
            for url_to_test in pidlist:
                found_at_google = self.query_google_webindex(url_to_test, pidlist)
                if found_at_google:
                    self.islisted = True
                    break

        if self.islisted:
            self.logger.info(
                "FsF-F4-01M : Found identifier in Google Dataset Search cache -:" + str(found_google_links)
            )
        else:
            self.logger.info("FsF-F4-01M : Identifier not listed in Google Dataset Search cache -:" + str(pidlist))

        return response

    def create_cache_db(self, google_cache_file):
        gs = pd.read_csv(google_cache_file)
        # google_cache_db_path = os.path.join(Preprocessor.fuji_server_dir, 'data','google_cache.db')
        con = sl.connect(self.google_cache_db_path)
        gf = pd.DataFrame(pd.concat([gs["url"], gs["doi"]]), columns=["uri"]).drop_duplicates()
        gf["source"] = 0
        gf.to_sql("google_links", con, if_exists="replace", index=False)
        with con:
            con.execute("CREATE INDEX google_uri_index ON google_links (uri) ")
        con.close()

    def add_google_search_record(self, url_to_save, source=1):
        # three sourced (int) : 0 = from kaggle file, 1 = from custom search match, 2 = google search (scraped)
        con = sl.connect(self.google_cache_db_path)
        try:
            with con:
                con.execute("INSERT INTO google_links (uri, source) values ('" + str(url_to_save) + "',1)")
            return
        except Exception as e:
            print("GOOGLE CACHE INSERT FAILED", e)
        con.close()
        return True
        ##test

    def query_google_webindex(self, url_to_test, pidlist):
        url_to_test = str(url_to_test).strip()
        google = "https://www.google.com/search?q=site:" + url_to_test + "&hl=en"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3538.102 Safari/537.36 Edge/18.19582"
        }
        found_url_in_google = False
        try:
            response = requests.get(google, headers=headers, cookies={"CONSENT": "YES+1"})
            soup = BeautifulSoup(response.content, "html.parser")
            not_indexed = re.compile("did not match any documents")
            if soup(text=not_indexed):
                found_url_in_google = False
            else:
                found_url_in_google = True
                for url_to_save in pidlist:
                    self.add_google_search_record(url_to_save)
                    sleep(randint(5, 20))
        except Exception as e:
            self.logger.warning("FsF-F4-01M : Google Index Query Error: -:" + str(e))
        return found_url_in_google

    def query_google_custom_search(self, url_to_test, pidlist):
        url_to_test = str(url_to_test).strip()
        if str(self.object_type).strip().lower() == "dataset":
            found_url_in_google = False
            if self.google_custom_search_id and self.google_custom_search_api_key:
                try:
                    google_url = (
                        "https://customsearch.googleapis.com/customsearch/v1?cx="
                        + self.google_custom_search_id
                        + "&q=url:"
                        + url_to_test
                        + "&key="
                        + self.google_custom_search_api_key
                    )
                    res = requests.get(google_url)
                    if res:
                        try:
                            google_json = res.json()
                            if google_json.get("items"):
                                for google_item in google_json.get("items"):
                                    if google_item.get("link") == url_to_test:
                                        for url_to_save in pidlist:
                                            self.add_google_search_record(url_to_save)
                                        found_url_in_google = True
                        except Exception as e:
                            print(e)
                except Exception as e:
                    self.logger.warning("FsF-F4-01M : Google Custom Search Query Error: -:" + str(e))
            return found_url_in_google

    def init_google_custom_search(self, custom_search_id, api_key):
        self.google_custom_search_id = custom_search_id
        self.google_custom_search_api_key = api_key

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
from fuji_server.helper.metadata_collector import MetaDataCollector
import feedparser


class MetaDataCollectorOreAtom(MetaDataCollector):
    """
    A class to collect the Object Reuse and Exchange (ORE) Atom metadata from the data. This class is child class of MetadataCollector.

    ...

    Attributes
    ----------
    source_name : str
        Source name of metadata
    target_url : str
        Target URL of the metadata

    Methods
    --------
    parse_metadata()
        Method to parse the ORE Atom metadata from the data.
    """
    source_name = None

    def __init__(self, loggerinst, target_url):
        """
        Parameters
        ----------
        loggerinst : logging.Logger
            Logger instance
        target_url : str
            Target URL
        """
        #self.is_pid = ispid
        self.target_url = target_url
        super().__init__(logger=loggerinst)

    def parse_metadata(self):
        """Parse the ORE Atom metadata from the data

        Returns
        ------
        str
            a string of source name
        dict
            a dictionary of ORE Atom metadata
        """
        self.content_type = 'application/atom+xml'
        ore_metadata = {}
        if self.target_url:
            self.source_name = self.getEnumSourceNames().OAI_ORE
            try:
                feed = feedparser.parse(self.target_url)
                if feed:
                    if feed.get('entries'):
                        if len(feed.get('entries')) == 1:
                            ore_metadata['title'] = feed.get('entries')[0].get('title')
                            ore_metadata['creator'] = feed.get('entries')[0].get('author')
                            ore_metadata['publisher'] = feed.get('entries')[0].get('source')
                            ore_metadata['publication_date'] = feed.get('entries')[0].get('published')
                            if feed.get('entries')[0].get('source'):
                                ore_metadata['publisher'] = feed.get('entries')[0].get('source').get('author')
                            ore_metadata['object_identifier'] = [feed.get('entries')[0].get('id')]
                            if feed.get('entries')[0].get('link'):
                                ore_metadata['object_identifier'].append(feed.get('entries')[0].get('link'))
                            if feed.get('entries')[0].get('link'):
                                pid = feed.get('entries')[0].get('link')
                                if pid != self.target_url:
                                    ore_metadata['object_identifier'] = feed.get('entries')[0].get('link')
                            if feed.get('entries')[0].get('links'):
                                ore_metadata['object_content_identifier'] = []
                                for link in feed.get('entries')[0].get('links'):
                                    if 'ore/terms/aggregates' in str(link.get('rel')):
                                        ore_metadata['object_content_identifier'].append({
                                            'url': str(link.get('href')),
                                            'type': str(link.get('type')),
                                            'size': str(link.get('length'))
                                        })
            except Exception as err:
                #print(err.with_traceback())
                self.logger.warning('FsF-F2-01M : Failed to parse OAI ORE XML -: {}'.format(err))
        else:
            self.logger.info('FsF-F2-01M : Could not identify OAI ORE metadata')

        return self.source_name, ore_metadata

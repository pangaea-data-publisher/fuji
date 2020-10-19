from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.models.identifier_included import IdentifierIncluded
from fuji_server.models.identifier_included_output import IdentifierIncludedOutput
from fuji_server.models.identifier_included_output_inner import IdentifierIncludedOutputInner
import urllib.request as urllib

class FAIREvaluatorContentIncluded(FAIREvaluator):
    def evaluate(self):
        self.result = IdentifierIncluded(id=self.count, metric_identifier=self.metric_identifier, metric_name=self.metric_name)
        self.output = IdentifierIncludedOutput()

        id_object = self.fuji.metadata_merged.get('object_identifier')
        self.output.object_identifier_included = id_object
        contents = self.fuji.metadata_merged.get('object_content_identifier')

        if id_object is not None:
            self.logger.info('FsF-F3-01M : Object identifier specified {}'.format(id_object))
        score = 0
        content_list = []
        if contents:
            if isinstance(contents, dict):
                contents = [contents]
            contents = [c for c in contents if c]
            number_of_contents = len(contents)
            self.logger.info('FsF-F3-01M : Number of object content identifier found - {}'.format(number_of_contents))

            if number_of_contents >= self.fuji.FILES_LIMIT:
                self.logger.info(
                    'FsF-F3-01M : The total number of object (content) specified is above threshold, so use the first {} content identifiers'.format(
                        self.fuji.FILES_LIMIT))
                contents = contents[:self.fuji.FILES_LIMIT]

            for content_link in contents:
                if content_link.get('url'):
                    # self.logger.info('FsF-F3-01M : Object content identifier included {}'.format(content_link.get('url')))
                    did_output_content = IdentifierIncludedOutputInner()
                    did_output_content.content_identifier_included = content_link
                    try:
                        # only check the status, do not download the content
                        response = urllib.urlopen(content_link.get('url'))
                        content_link['header_content_type'] = response.getheader('Content-Type')
                        content_link['header_content_type'] = str(content_link['header_content_type']).split(';')[0]
                        content_link['header_content_length'] = response.getheader('Content-Length')
                        if content_link['header_content_type'] != content_link.get('type'):
                            self.logger.warning('FsF-F3-01M : Content type given in metadata (' + str(content_link.get(
                                'type')) + ') differs from content type given in Header response (' + str(
                                content_link['header_content_type']) + ')')
                            self.logger.info(
                                'FsF-F3-01M : Replacing metadata content type with content type from Header response: ' + str(
                                    content_link['header_content_type']))
                            content_link['type'] = content_link['header_content_type']
                        # will pass even if the url cannot be accessed which is OK
                        # did_result.test_status = "pass"
                        # did_score.earned=1
                    except urllib.HTTPError as e:
                        self.logger.warning(
                            'FsF-F3-01M : Content identifier {0} inaccessible, HTTPError code {1} '.format(
                                content_link.get('url'), e.code))
                    except urllib.URLError as e:
                        self.logger.exception(e.reason)
                    except:
                        self.logger.warning('FsF-F3-01M : Could not access the resource')
                    else:  # will be executed if there is no exception
                        self.fuji.content_identifier.append(content_link)
                        did_output_content.content_identifier_active = True
                        content_list.append(did_output_content)
                else:
                    self.logger.warning('FsF-F3-01M : Object (content) url is empty - {}'.format(content_link))
        else:
            self.logger.warning('FsF-F3-01M : Data (content) identifier is missing.')

        if content_list:
            score += 1
        self.score.earned = score
        if score > 0:
            self.result.test_status = "pass"
        self.output.content = content_list
        self.result.output = self.output
        self.result.score = self.score

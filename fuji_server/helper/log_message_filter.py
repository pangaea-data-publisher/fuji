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

import logging

logger = logging.getLogger(__name__)


class MessageFilter(logging.Filter):

    def __init__(self):
        self.messages = {}

    def filter(self, record):
        # Intercept logs messages #TODO - do not write FsF-* messages into a log file
        if record.getMessage().startswith('FsF-'):
            level = record.levelname
            m = record.getMessage().split(":", 1)
            msg = level + ': ' + m[1].strip()
            metric = m[0].strip()
            if metric in self.messages:
                self.messages[metric].append(msg)
            else:
                self.messages[metric] = [msg]
        return True

    def getMessage(self, m_id):
        # return debug messages by metric id or return None
        return self.messages.get(m_id)

# class RequestsHandler(logging.Handler):
#     messages = []
#     def emit(self, record):
#         self.messages.append(record.getMessage())

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

# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import logging


class MessageFilter(logging.Filter):
    def __init__(self):
        self.messages = {}

    def filter(self, record):
        # Intercept logs messages #TODO - do not write FsF-* messages into a log file
        # print(record.getMessage())
        if record.msg.startswith("FsF-"):
            level = record.levelname
            m = record.msg.split(":", 1)
            msg = f"{level}: {m[1].strip()}"
            record.msg = msg
        return True

    def getMessage(self, m_id):
        # return debug messages by metric id or return None
        return self.messages.get(m_id)


# class RequestsHandler(logging.Handler):
#     messages = []
#     def emit(self, record):
#         self.messages.append(record.getMessage())

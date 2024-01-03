# from connexion.apps.flask_app import FlaskJSONEncoder
from connexion.jsonifier import JSONEncoder

from fuji_server.models.base_model_ import Model


class CustomJSONEncoder(JSONEncoder):
    include_nulls = False

    def default(self, o):
        if isinstance(o, Model):
            dikt = {}
            for attr, _ in o.swagger_types.items():
                value = getattr(o, attr)
                if value is None and not self.include_nulls:
                    continue
                attr = o.attribute_map[attr]
                dikt[attr] = value
            return dikt
        return JSONEncoder.default(self, o)

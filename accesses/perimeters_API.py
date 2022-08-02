from typing import Dict


class ApiPerimeter:
    id: str
    names: Dict[str, str]
    type: str
    parent_id: str

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', None)
        self.names = kwargs.get('names', None)
        self.type = kwargs.get('type', None)
        self.parent_id = kwargs.get('parent_id', None)

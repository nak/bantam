class HTTPException(Exception):

    def __init__(self, code: int, msg: str):
        super().__init__(msg)
        self._code = code

    @property
    def status_code(self):
        return self._code

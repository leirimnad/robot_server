class _ServerMessages:
    @property
    def server_key_request(self) -> bytes: return b"107 KEY REQUEST"

    @property
    def server_ok(self) -> bytes: return b"200 OK"

    @property
    def server_key_out_of_range_error(self) -> bytes: return b"303 KEY OUT OF RANGE"

    @property
    def server_syntax_error(self) -> bytes: return b"301 SYNTAX ERROR"

    @staticmethod
    def server_confirmation(server_hash: int) -> bytes:
        return str(server_hash).encode()


server_messages = _ServerMessages()

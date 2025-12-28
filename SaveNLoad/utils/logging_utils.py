import logging

class SuppressEndpointFilter(logging.Filter):
    """
    Filter to suppress logs for specific endpoints.
    Useful for removing noise from polling endpoints (e.g. /api/client/pending/).
    """
    def __init__(self, endpoints=None):
        super().__init__()
        self.endpoints = endpoints or []

    def filter(self, record):
        # The message usually contains the URL path.
        # For django.server logs, args[0] might be the full request line "GET /path/ HTTP/1.1"
        message = record.getMessage()
        
        for endpoint in self.endpoints:
            if endpoint in message:
                return False
        return True

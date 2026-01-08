from django.conf import settings


class ContentSecurityPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.policy = getattr(settings, 'CSP_POLICY', '').strip()

    def __call__(self, request):
        response = self.get_response(request)
        if self.policy and 'Content-Security-Policy' not in response:
            response['Content-Security-Policy'] = self.policy
        return response

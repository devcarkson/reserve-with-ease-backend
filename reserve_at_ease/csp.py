"""
Content Security Policy middleware to prevent Chrome's Private Network Access prompt.

This adds CSP headers that tell browsers:
1. Only connect to the production origin (franccj.com.ng)
2. Don't treat subdirectory requests as private network access
"""

class CSPMiddleware:
    """
    Middleware to add Content Security Policy headers.
    
    This helps prevent Chrome's "Private Network Access" prompt by explicitly
    allowing connections to the backend subdirectory from the frontend origin.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Get the origin from the request
        origin = request.META.get('HTTP_ORIGIN', '')
        
        # Add CSP header that allows connections to the same origin
        # This prevents Chrome from treating subdirectory API calls as private network access
        csp_value = (
            "connect-src 'self' "
            "https://franccj.com.ng "
            "https://*.franccj.com.ng "
            "'unsafe-inline' "
            "'unsafe-eval';"
        )
        
        # Only add CSP for HTML responses (not for API/JSON responses)
        content_type = response.get('Content-Type', '')
        if 'text/html' in content_type:
            response['Content-Security-Policy'] = csp_value
            # Also add X-Content-Security-Policy for older browsers
            response['X-Content-Security-Policy'] = csp_value
        
        return response

import threading

_thread_locals = threading.local()

def get_current_request_ip():
    return getattr(_thread_locals, 'ip_address', None)

def get_current_user():
    return getattr(_thread_locals, 'user', None)

class ActivityLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        _thread_locals.ip_address = ip
        _thread_locals.user = request.user if request.user.is_authenticated else None
        
        response = self.get_response(request)
        
        # Cleanup thread locals
        if hasattr(_thread_locals, 'ip_address'):
            del _thread_locals.ip_address
        if hasattr(_thread_locals, 'user'):
            del _thread_locals.user
            
        return response

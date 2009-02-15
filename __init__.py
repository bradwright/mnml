import cgi
import re

# limit exports
__all__ = [
    'HttpRequest', 'HttpResponse', 'WebApplication'
]

class HttpError(Exception):
    pass


class HttpRequest(object):
    """A single HTTP request"""
    def __init__(self, environ):
        self.method = environ['REQUEST_METHOD']
        
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html
        if self.method not in ('POST', 'GET', 'DELETE', 'PUT', 'HEAD', 'OPTIONS', 'TRACE'):
            raise HttpError, "Invalid request"
        
        self.POST = self.GET = {}
        
        if len(environ['QUERY_STRING']):
            self.GET = cgi.parse_qs(environ['QUERY_STRING'])
            print self.GET
        
        if self.method == 'POST':
            self.POST = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ, keep_blank_values=1)
        
        # like PHP's $_REQUEST - but you should usually be more explicit
        self.REQUEST = self.GET.copy()
        self.REQUEST.update(self.POST)


class HttpResponse(object):
    """A single HTTP response"""
    status_codes = {
        200: "OK",
        201: "Created",
        202: "Accepted",
        301: "Moved Permanently",
        302: "Found",
        303: "See Other",
        304: "Not Modified",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        410: "Gone",
        500: "Internal Server Error",
    }
    
    def __init__(self, content='', headers={}, status_code=200):
        self.status_code = status_code
        self.set_content(content)
        self.headers = headers
        self.headers['content-length'] = str(len(content))
        
        if not 'content-type' in self.headers:
            self.headers['content-type'] = 'text/html'
    
    def get_status(self):
        if self.status_code not in self.status_codes:
            self.status_code = 500
        return "%s %s" % (self.status_code, self.status_codes[self.status_code])
    
    def set_status(self, code):
        self.status_code = code
    
    def get_headers(self):
        return list(self.headers.iteritems())
    
    def set_headers(self, *args):
        """takes either a key/value or a dictionary"""
        if type(args[0]).__name__ == 'dict':
            self.headers.update(args[0])
        else:
            key, value = args
            self.headers[key] = value
    
    def get_content(self):
        return [self._content, '\n']
    
    def set_content(self, value):
        # http://www.python.org/dev/peps/pep-0333/#unicode-issues
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        self._content = value
    
    content = property(get_content, set_content)
    status = property(get_status, set_status)
    #headers = property(get_headers, set_headers)


class WebApplication(object):
    """The actual serving of Python code is done here"""
    def __init__(self, routes):
        self.routes = tuple((re.compile(a), b) for a,b in routes)
    
    def __call__(self, environ, start_response):
        request = HttpRequest(environ)
        response = None
        
        for route in self.routes:
            url, view = route
            match = url.match(environ['PATH_INFO'])
            if match:
                if hasattr(view, '__call__'):
                    to_call = view
                else:
                    # TODO: do this better
                    to_call = eval(view)
                try:
                    response = to_call(request, **match.groupdict())
                except Exception, error:
                    # either the function failed, or it doesn't exist
                    # TODO: log missing functions
                    try:
                        # see if there's a user-defined error route
                        response = error500(request, error)
                    except NameError:
                        # custom 500 function missing, return generic
                        msg = '<h1>500 Error</h1><pre>%s</pre>' % error
                        response = HttpResponse(msg, status_code=500)
                    except Exception, e:
                        # custom 500 function there, but broken
                        msg = '<h1>500 Error</h1><pre>%s</pre>' % e
                        response = HttpResponse(msg, status_code=500)
                finally:
                    break
        
        if not isinstance(response, HttpResponse):
            try:
                response = error404(request)
            except Exception, e:
                response = HttpResponse('<h1>Page Not Found</h1>', status_code=404)
        start_response(response.status, response.get_headers())
        return response.content
    

if __name__ == '__main__':
    """run the basic server"""
    routes = (
        (r'^/$', 'homepage'),
    )
    
    def homepage(request):
        return HttpResponse('hello world!')
    
    web_app = WebApplication(routes)
    
    try:
        from wsgiref.simple_server import make_server
        server = make_server('', 8000, web_app)
        server.serve_forever()
    except KeyboardInterrupt:
        import sys
        print "Server stopping"
        sys.exit()
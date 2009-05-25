# NOTE:
# At the moment this script borrows fairly heavily from newf, since that's 
# basically the bare minimum code required for a routed WSGI framework.

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
        self._headers = headers
        self._headers['content-length'] = str(len(content))
        
        if not headers.get('content-type'):
            self._headers['content-type'] = 'text/html'
    
    def get_status(self):
        if self.status_code not in self.status_codes:
            self.status_code = 500
        return "%s %s" % (self.status_code, self.status_codes[self.status_code])
    
    def set_status(self, code):
        self.status_code = code
    
    def get_headers(self):
        return list(self._headers.iteritems())
    
    def set_headers(self, *args):
        """takes either a key/value or a dictionary"""
        if type(args[0]).__name__ == 'dict':
            self._headers.update(args[0])
        else:
            key, value = args
            self._headers[key] = value
    
    def get_content(self):
        # content-type is always set because of the init method, so don't need 
        # to check for its existence
        if self._headers['content-type'].startswith('text'):
            return [self._content, '\n']
        return [self._content]
    
    def set_content(self, value):
        # http://www.python.org/dev/peps/pep-0333/#unicode-issues
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        self._content = value
    
    content = property(get_content, set_content)
    status = property(get_status, set_status)
    headers = property(get_headers, set_headers)


class UrlRouting(object):
    """Master class for routing URLs"""
    def __init__(self, routes):
        self.routes = [(re.compile(self._compile_route(pair[0])), pair[1]) for pair in routes]
    
    def add_route(self, route):
        self.routes.append(route)
    
    def get_view(self, url):
        """returns a matched view to the passed URL"""
        for pair in self.routes:
            route, to_call = pair
            matches = route.match(url)
            if matches:
                return to_call, matches.groupdict()
        return None
    
    def reverse(self, route_name, **kwargs):
        """returns a matched URL composed of kwargs"""
        for pair in self.routes:
            route, view = pair
    
    def _compile_route(self, route):
        """returns a compiled regular expression"""
        # chop off leading slash
        if route.startswith('/'):
            route = route[1:]
        
        trailing_slash = False
        # check end slash and remember to keep it
        if route.endswith('/'):
            route = route[:-1]
            trailing_slash = True
        
        # split into path components
        bits = route.split('/')
    
        # compiled match starts with a slash,
        #  so we make it a list so we can join later
        regex = ['']
        for path_component in bits:
            if path_component.startswith(':'):
                # it's a route, so compile
                name = path_component[1:]
                # accept only valid URL characters
                regex.append(r'(?P<%s>[-_a-zA-Z0-9+%%]+)' % name)
            else:
                # just a string/static path component
                regex.append(path_component)
            
        # stick the trailing slash back on
        if trailing_slash:
            regex.append('')
        
        # stitch it back together as a path
        return '^%s$' % '/'.join(regex)
    

class RegexRouting(UrlRouting):
    """Regex-based URL routing"""
    pass

class WebApplication(object):
    """The actual serving of Python code is done here"""
    def __init__(self, routes):
        # cache routes
        if hasattr(routes, 'get_view'):
            self.routes = routes
        else:
            self.routes = UrlRouting(routes)
    
    def __call__(self, environ, start_response):
        request = HttpRequest(environ)
        response = None
        
        view, args = self.routes.get_view(environ['PATH_INFO'])
        if view:
            if hasattr(view, '__call__'):
                to_call = view
            else:
                # TODO: do this better
                to_call = eval(view)
            try:
                response = to_call(request, **args)
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
        
        if not isinstance(response, HttpResponse):
            try:
                response = error404(request)
            except Exception, e:
                response = HttpResponse('<h1>Page Not Found</h1>', status_code=404)
        start_response(response.status, response.get_headers())
        return response.content
    
    def run(self):
        from wsgiref.handlers import BaseHandler
        handler = BaseHandler()
        handler.run(self)
    
    def dev_run(self, port=8000):
        from wsgiref.simple_server import make_server
        server = make_server('', port, self)
        print 'MNML now running on http://127.0.0.1:%s\n' % port
        try:
            server.serve_forever()
        except:
            print 'MNML stopping...'
            server.socket.close()
    

if __name__ == '__main__':
    """run the basic server"""
    routes = (
        ('/', 'homepage'),
        ('/myview/:stuff/', 'other_thing')
    )
    
    def homepage(request):
        return HttpResponse('hello world!')
    
    def other_thing(request, stuff):
        return HttpResponse('found stuff: %s!' % stuff)
    
    web_app = WebApplication(routes)
    
    try:
        web_app.dev_run(8000)
    except KeyboardInterrupt:
        import sys
        print "Server stopping"
        sys.exit()

# -*- coding: utf-8 -*-

import webapp2 as webapp
import webapp2_extras.json as json_extras


MIMETYPES = {'xml' : 'application/xml', 'json' : 'text/json', 'xhtml' : 'application/xhtml+xml', 'html' : 'text/html'}

class Resource(webapp.Route):
    """An Resource class that adds redirect_to and strict_slash options.
        """
    def __init__(self, template, handler=None, name=None, defaults=None,
                 build_only=False, accept_mimetypes=None, default_display='json'):
        super(Resource, self).__init__(template, handler, name, defaults,
                                       build_only)
        
        self.accept_mimetypes = accept_mimetypes
        self.default_display = default_display
        
        def __repr__(self):
            return '<Resource(%r, %r, name=%r, defaults=%r, build_only=%r), accept_mimetypes%r, default_display=%r>' % \
                (self.template, self.handler, self.name, self.defaults,
                 self.build_only, accept_mimetypes, default_display)

class ResourceHandler(webapp.RequestHandler):
    def __init__(self, request=None, response=None):
        """Initializes this request handler with the given WSGI application,
            Request and Response.
            
            .. note::
            Parameters are optional only to support webapp's constructor which
            doesn't take any arguments. Consider them as required.
            
            :param request:
            A :class:`Request` instance.
            :param response:
            A :class:`Response` instance.
            """
        self.short_response_mime, self.response_mime = self._best_mime_match(request)
        self.method = request.method
        super(ResourceHandler, self).__init__(request, response)
    
    def _best_mime_match(self, request):
        # Make sure to ONLY get MIMES which are in MIMETYEPS, so we can be sure to always return a valid MIMETYPE.
        # do not get mimetype user requested which we don't have
        # Need to maintain order of accept_mimetypes that is why we create tuples and then dict
        mimetypes = dict((MIMETYPES[key], key) for key in request.route.accept_mimetypes if key in MIMETYPES)
        full_mimes, short_mimes = zip(*mimetypes.items())
        #accept.best_match() returns result in wrong order so mst reverse list
        response_mime = request.accept.best_match(reversed(full_mimes))
        short_response_mime = mimetypes.get(response_mime)
        return short_response_mime, response_mime
    
    def dispatch(self):
        """Dispatches the request.
            
            This will first check if there's a handler_method defined in the
            matched route, and if not it'll use the method correspondent to the
            request method (get, post etc).
            """
        method_name = self.request.route.handler_method
        if not method_name:
            method_name = self.request.method
        
        method = getattr(self, method_name, None)
        if method is None:
            # 405 Method Not Allowed.
            # The response MUST include an Allow header containing a
            # list of valid methods for the requested resource.
            # http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.4.6
            valid = ', '.join(self.get_valid_methods())
            self.abort(405, headers=[('Allow', valid)])
        
        try:
            results = method(*self.request.route_args, **self.request.route_kwargs)
        except Exception, e:
            self.handle_exception(e, self.app.debug)
        
        self.dispatch_display(results)
    
    def dispatch_display(self, results):
        display_handler_name = '_'.join((self.method, self.short_response_mime))
        method = getattr(self, display_handler_name, None)
        self.response.headers['x-BEST-MIME'] = display_handler_name
        if not method:
            display_handler_name = '_'.join((self.method, self.request.route.default_display))
            self.response_mime = MIMETYPES[self.request.route.default_display]
            method = getattr(self, display_handler_name, None)
        try:
            self.response.headers['Content-Type'] = self.response_mime
            self.response.charset = 'utf-8'
            self.response.out.write(method(results))
        except Exception, e:
            self.handle_exception(e, self.app.debug)
    
    def POST_json(self, results):
        return self.GET_json(results)
    
    def GET_json(self, results):
        serialized = json_extras.encode(results)
        return serialized
    
    def _normalize_method(self, method):
        return method.lower().replace('-', '_')

from django.http import HttpResponse

class APIException(Exception):
    pass

class HttpResponseNotAcceptable(HttpResponse):
    status_code = 406

class HttpResponseCreated(HttpResponse):
    '''Return an HTTP 201 Created response. The parameter for the Location field is required;
      this should be the URL to the created resource.'''
    status_code = 201

    def __init__(self, location):
        HttpResponse.__init__(self)
        self['Location'] = location


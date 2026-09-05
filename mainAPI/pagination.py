from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class CustomPageNumberPagination(PageNumberPagination):
    def get_paginated_response(self, data):
        next_page = -1
        if self.page.has_next():
            next_page = self.page.next_page_number()
            
        previous_page = -1
        if self.page.has_previous():
            previous_page = self.page.previous_page_number()

        return Response({
            'count': self.page.paginator.count,
            'next': next_page,
            'previous': previous_page,
            'results': data
        })

    def get_paginated_response_schema(self, schema):
        return {
            'type': 'object',
            'properties': {
                'count': {
                    'type': 'integer',
                    'example': 123,
                },
                'next': {
                    'type': 'integer',
                    'example': 2,
                    'description': 'Page number of the next page. Returns -1 when unavailable.',
                },
                'previous': {
                    'type': 'integer',
                    'example': -1,
                    'description': 'Page number of the previous page. Returns -1 when unavailable.',
                },
                'results': schema,
            },
        }

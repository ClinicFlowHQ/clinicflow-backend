from rest_framework.pagination import PageNumberPagination


class FlexiblePageNumberPagination(PageNumberPagination):
    """
    Pagination class that allows clients to specify page_size via query parameter.
    - Default: 10 items per page
    - Max: 500 items per page
    - Query param: ?page_size=50
    """
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 500

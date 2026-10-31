from rest_framework.pagination import PageNumberPagination


class Paginasi(PageNumberPagination):
    page_size = 25
    page_size_query_param = "ukuran"
    max_page_size = 200

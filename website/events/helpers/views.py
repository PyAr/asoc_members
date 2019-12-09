from django.db.models import Q
import functools
import operator


def search_filtered_queryset(base_queryset, search_fields, search_value):
    filters = []
    for key, value in search_fields.items():
        field_filter = key
        if value != 'equal':
            field_filter = field_filter + '__' + value
        filter_dict = {field_filter: search_value}
        filters.append(Q(**filter_dict))
    queryset = base_queryset.filter(functools.reduce(operator.or_, filters))
    return queryset

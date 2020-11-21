import typing as t

from sqlalchemy import types

from deckeditor.sorting.sorting import SortProperty


class SortPropertyField(types.TypeDecorator):
    impl = types.String

    def process_bind_param(self, value: t.Optional[t.Type[SortProperty]], dialect) -> t.Optional[str]:
        if value is None:
            return None
        return value.name

    def process_result_value(self, value: t.Optional[str], dialect) -> t.Optional[t.Type[SortProperty]]:
        if not value:
            return None
        return SortProperty.names_to_sort_property[value]

    def process_literal_param(self, value, dialect):
        pass

    @property
    def python_type(self):
        return type

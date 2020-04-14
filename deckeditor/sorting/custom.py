from __future__ import annotations

import pickle
import typing as t

from mtgorp.models.persistent.cardboard import Cardboard

from deckeditor import paths


class CustomSortMap(dict):
    enabled_properties = ('cmc', 'colors')

    def chained_get(self, keys: t.Iterable[str], default: t.Any = None) -> t.Any:
        v = self
        try:
            for key in keys:
                v = v[key]
        except KeyError:
            return default
        return v

    def get_cardboard_value(self, cardboard: Cardboard, sort_property: str, default: t.Any = None) -> t.Any:
        return self.chained_get(('cardboards', cardboard.name, sort_property), default = default)

    def set_cardboard_value(self, cardboard: Cardboard, sort_property: str, value: t.Any) -> None:
        try:
            self['cardboards'][cardboard.name][sort_property] = value
        except KeyError:
            self['cardboards'][cardboard.name] = {sort_property: value}

    def unset_cardboard_value(self, cardboard: Cardboard, sort_property: str) -> None:
        try:
            del self['cardboards'][cardboard.name][sort_property]
        except KeyError:
            pass

    @classmethod
    def empty(cls) -> CustomSortMap:
        return CustomSortMap(
            {
                'cardboards': {},
                'printings': {},
            }
        )

    @classmethod
    def load(cls) -> CustomSortMap:
        try:
            with open(paths.CUSTOM_SORT_MAP_PATH, 'rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            return cls.empty()

    def save(self) -> None:
        with open(paths.CUSTOM_SORT_MAP_PATH, 'wb') as f:
            pickle.dump(self, f)

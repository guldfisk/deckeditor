import typing as t


class OptionsSelector(object):
    def update_content(self, options: t.Mapping[str, t.Any], enabled: bool) -> None:
        raise NotImplementedError()

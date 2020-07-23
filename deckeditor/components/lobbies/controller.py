from __future__ import annotations

import typing as t

from PyQt5.QtCore import QObject, pyqtSignal

from cubeclient.models import VersionedCube

from deckeditor.context.context import Context


class LobbiesController(QObject):
    versioned_cubes_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._versioned_cubes: t.List[VersionedCube] = []
        self._release_versioned_cube_map: t.MutableMapping[int, VersionedCube] = {}

        Context.token_changed.connect(self._refresh)

    @property
    def versioned_cubes(self) -> t.List[VersionedCube]:
        return self._versioned_cubes

    @property
    def release_versioned_cube_map(self) -> t.Mapping[int, VersionedCube]:
        return self._release_versioned_cube_map

    def _refresh(self, token: t.Optional[str]) -> None:
        if token is None:
            return
        Context.cube_api_client.versioned_cubes(limit = 50).then(self._set_versioned_cubes)

    def _set_versioned_cubes(self, versioned_cubes: t.List[VersionedCube]) -> None:
        self._versioned_cubes = list(versioned_cubes)
        self._release_versioned_cube_map = {
            release.id: versioned_cube
            for versioned_cube in
            self._versioned_cubes
            for release in
            versioned_cube.releases
        }


LOBBIES_CONTROLLER = LobbiesController()
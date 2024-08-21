from __future__ import annotations

from bidict import bidict
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox

from deckeditor.components.lobbies.interfaces import LobbiesViewInterface
from deckeditor.components.lobbies.lobby import LobbyView
from deckeditor.context.context import Context


class LobbyTabs(QtWidgets.QTabWidget):
    def __init__(self, parent: LobbiesViewInterface):
        super().__init__(parent)
        self._lobby_view: LobbiesViewInterface = parent

        self.setTabsClosable(True)
        self.setMovable(True)

        self.tabCloseRequested.connect(self._tab_close_requested)
        self._lobby_view.lobby_model.changed.connect(self._update_content)

        self._tabs_map: bidict[str, int] = bidict()

    def _update_content(self) -> None:
        lobbies = {
            name: lobby
            for name, lobby in self._lobby_view.lobby_model.get_lobbies().items()
            if Context.cube_api_client.user.username in lobby.users
        }

        removed = self._tabs_map.keys() - lobbies.keys()
        if removed:
            for removed_name, removed_index in sorted(
                ((name, self._tabs_map[name]) for name in removed),
                key=lambda kv: kv[1],
                reverse=True,
            ):
                del self._tabs_map[removed_name]

                for name, index in self._tabs_map.items():
                    if index > removed_index:
                        self._tabs_map[name] -= 1

                self.removeTab(removed_index)

        added = lobbies.keys() - self._tabs_map.keys()
        if added:
            max_index = max(self._tabs_map.values()) if self._tabs_map else -1
            for added_name in added:
                max_index += 1
                self._tabs_map[added_name] = max_index
                self.insertTab(
                    max_index,
                    LobbyView(self._lobby_view.lobby_model, added_name),
                    added_name,
                )

    def _tab_close_requested(self, index: int) -> None:
        closed_tab: LobbyView = self.widget(index)

        if closed_tab.lobby.state == "game":
            confirm_dialog = QMessageBox()
            confirm_dialog.setText("Confirm close")
            confirm_dialog.setInformativeText(
                "You sure you want to disconnect from this ongoing game?\nYou cannot reconnect after leaving."
            )
            confirm_dialog.setStandardButtons(QMessageBox.Close | QMessageBox.Cancel)
            confirm_dialog.setDefaultButton(QMessageBox.Cancel)
            return_code = confirm_dialog.exec_()

            if return_code == QMessageBox.Cancel:
                return

        self._lobby_view.lobby_model.leave_lobby(self._tabs_map.inverse[index])

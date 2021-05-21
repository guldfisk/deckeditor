import datetime
import functools
import logging
import typing as t

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QColor

from promise import Promise
from pyqtgraph import PlotWidget, mkPen, AxisItem

from mtgorp.models.interfaces import Cardboard

from magiccube.collections.cubeable import CardboardCubeable
from magiccube.laps.traps.trap import CardboardTrap, IntentionType
from magiccube.laps.traps.tree.printingtree import CardboardNodeChild

from cubeclient.models import RatingPoint, NodeRatingPoint

from deckeditor.authentication.login import LOGIN_CONTROLLER
from deckeditor.components.cardview.focuscard import FocusEvent, focusable_as_cardboards
from deckeditor.context.context import Context


class TimeAxisItem(AxisItem):

    def tickStrings(self, values, scale, spacing):
        return [datetime.datetime.fromtimestamp(value).strftime('%Y-%m-%d') for value in values]


class RatingView(QtWidgets.QWidget):
    _ratings_ready = QtCore.pyqtSignal(object, object)
    _node_ratings_ready = QtCore.pyqtSignal(object)

    def __init__(self):
        super().__init__()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._cubeable_plot = PlotWidget(axisItems = {'bottom': TimeAxisItem(orientation = 'bottom')})
        self._nodes_plot = PlotWidget(axisItems = {'bottom': TimeAxisItem(orientation = 'bottom')})

        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 1)

        layout.addWidget(self._splitter)

        self._splitter.addWidget(self._cubeable_plot)
        self._splitter.addWidget(self._nodes_plot)

        self._display_target: t.Optional[t.Tuple[int, CardboardCubeable]] = None

        self._ratings_ready.connect(self._set_cubeable_ratings)
        self._node_ratings_ready.connect(self._set_nodes_ratings)
        LOGIN_CONTROLLER.login_success.connect(self._on_login)

    @classmethod
    def _get_color(cls, n: int = 0) -> QColor:
        return QColor(100 + (n * 70) % 155, 100 + ((n + 1) * 50) % 155, 100 + ((n + 2) * 40) % 155)

    @functools.lru_cache(maxsize = 128)
    def _get_rating_points(self, release_id: int, cardboard_cubeable: CardboardCubeable) -> Promise[t.Sequence[RatingPoint]]:
        return Context.cube_api_client.rating_history_for_cardboard_cubeable(
            release_id,
            cardboard_cubeable,
        )

    @functools.lru_cache(maxsize = 256)
    def _get_node_rating_points(self, release_id: int, node: CardboardNodeChild) -> Promise[t.Sequence[NodeRatingPoint]]:
        return Context.cube_api_client.rating_history_for_node(
            release_id,
            node,
        ).then(lambda ratings: (node, ratings))

    def _on_login(self, *args, **kwargs) -> None:
        self._get_rating_points.cache_clear()
        self._get_node_rating_points.cache_clear()

    def _set_cubeable_ratings(self, cardboard_cubeable: CardboardCubeable, ratings: t.Sequence[RatingPoint]) -> None:
        self._cubeable_plot.clear()
        data_item = self._cubeable_plot.plot([p.rating_map.created_at.timestamp() for p in ratings], [p.rating for p in ratings])
        legend = self._cubeable_plot.addLegend(labelTextSize = '15pt')
        legend.addItem(data_item, cardboard_cubeable.name if isinstance(cardboard_cubeable, Cardboard) else cardboard_cubeable.description)
        self._cubeable_plot.getPlotItem().enableAutoRange()

    def _set_nodes_ratings(self, ratings: t.Iterable[t.Tuple[CardboardNodeChild, t.Sequence[NodeRatingPoint]]]) -> None:
        self._nodes_plot.show()
        self._nodes_plot.clear()
        legend = self._nodes_plot.addLegend(labelTextSize = '15pt')

        for idx, (node_child, ratings) in enumerate(ratings):
            data_item = self._nodes_plot.plot(
                [p.rating_map.created_at.timestamp() for p in ratings],
                [p.rating for p in ratings],
                pen = mkPen(color = self._get_color(idx)),
            )
            legend.addItem(data_item, node_child.name if isinstance(node_child, Cardboard) else node_child.get_minimal_string())
        self._nodes_plot.getPlotItem().enableAutoRange()

    def on_focus_event(self, focus_event: FocusEvent) -> None:
        if not self.isVisible() or not focus_event.release_id or Context.focus_card_frozen:
            return

        cardboard_cubeable = focusable_as_cardboards(focus_event.focusable)

        display_target = (focus_event.release_id, cardboard_cubeable)
        if display_target == self._display_target:
            return
        self._display_target = display_target

        promise = self._get_rating_points(focus_event.release_id, cardboard_cubeable)

        if promise.is_pending:
            promise.then(
                lambda ratings: self._ratings_ready.emit(
                    cardboard_cubeable, ratings
                )
            ).catch(
                logging.warning
            )
        elif promise.is_fulfilled:
            self._set_cubeable_ratings(cardboard_cubeable, promise.get())

        if isinstance(cardboard_cubeable, CardboardTrap) and cardboard_cubeable.intention_type == IntentionType.GARBAGE:
            promise = Promise.all(
                [
                    self._get_node_rating_points(focus_event.release_id, node)
                    for node in
                    cardboard_cubeable.node.children.distinct_elements()
                ]
            )
            if promise.is_pending:
                promise.then(
                    self._node_ratings_ready.emit
                ).catch(
                    logging.warning
                )
            elif promise.is_fulfilled:
                self._set_nodes_ratings(promise.get())
        else:
            self._nodes_plot.hide()

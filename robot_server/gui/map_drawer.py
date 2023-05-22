from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QPen
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene

from robot_server.bridge.thread_event import MapState


class MapDrawer:
    def __init__(self, graphics_view: QGraphicsView):
        self._graphics_view = graphics_view
        self._max_coordinate = None
        self._scene = QGraphicsScene()
        self._graphics_view.setScene(self._scene)
        self._graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scene_rect = QRectF(self._graphics_view.rect())
        self._scene.setSceneRect(scene_rect)
        self._scene_size = scene_rect.width() - 1
        self._cell_size = None
        self._previous_position: tuple[int, int] = None

    def update_map(self, map_state: MapState):
        if self._max_coordinate is None:
            x, y = map_state.position
            self._max_coordinate = max(abs(x), abs(y)) + 2
            self._draw_grid(self._max_coordinate)

        if self._previous_position is not None:
            self._draw_path(*self._previous_position, *map_state.position)

        for x, y in map_state.banned_positions:
            self._draw_obstacle(x, y)

        self._previous_position = map_state.position

    def _draw_grid(self, max_coordinate: int):

        num_rows = num_columns = max_coordinate * 2
        self._cell_size = self._scene_size / num_columns
        grid_color = Qt.lightGray
        pen = QPen(grid_color, 1, Qt.SolidLine)

        for row in range(1, num_rows):
            y = row * self._cell_size
            self._scene.addLine(0, y, self._scene_size, y, pen)

        for column in range(1, num_columns):
            x = column * self._cell_size
            self._scene.addLine(x, 0, x, self._scene_size, pen)

        # axes
        pen = QPen(Qt.black, 1, Qt.SolidLine)
        self._scene.addLine(0, self._scene_size / 2, self._scene_size, self._scene_size / 2, pen)
        self._scene.addLine(self._scene_size / 2, 0, self._scene_size / 2, self._scene_size, pen)

    def _draw_obstacle(self, x: int, y: int):
        size = self._cell_size // 4
        x_pos = self._scene_size / 2 + x * self._cell_size
        y_pos = self._scene_size / 2 - y * self._cell_size
        pen = QPen(Qt.red, 2, Qt.SolidLine)
        # draw a cross
        self._scene.addLine(x_pos - size, y_pos - size, x_pos + size, y_pos + size, pen)
        self._scene.addLine(x_pos - size, y_pos + size, x_pos + size, y_pos - size, pen)

    def _draw_path(self, x1: int, y1: int, x2: int, y2: int):
        x1_pos = self._scene_size / 2 + x1 * self._cell_size
        y1_pos = self._scene_size / 2 - y1 * self._cell_size
        x2_pos = self._scene_size / 2 + x2 * self._cell_size
        y2_pos = self._scene_size / 2 - y2 * self._cell_size
        pen = QPen(Qt.blue, 2, Qt.SolidLine)
        self._scene.addLine(x1_pos, y1_pos, x2_pos, y2_pos, pen)

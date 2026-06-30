# ============================================================
# Imports
# ============================================================
import sys
import json

from PyQt5.QtWidgets import (
    QApplication,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsEllipseItem,
    QGraphicsTextItem,
)
from PyQt5.QtGui import (
    QPixmap,
    QPen,
    QPainterPath,
    QPainter,
    QColor,
)
from PyQt5.QtCore import Qt, QPointF


# ============================================================
# Configuration Constants
# ============================================================
JSON_PATH = "data/map_data.json"
NODE_RADIUS = 6

# Node colors
COLOR_NODE_NORMAL = QColor(190, 0, 50)

# Edge outline color
COLOR_PATH_OUTLINE = QColor(70, 70, 70, 200)

# Traffic-based edge colors
COLOR_PATH_TRAFFIC_GREEN = QColor(0, 200, 0)      # Low traffic
COLOR_PATH_TRAFFIC_ORANGE = QColor(255, 165, 0)   # Medium traffic
COLOR_PATH_TRAFFIC_RED = QColor(255, 0, 0)        # High traffic


# ============================================================
# Map Viewer Class
# ============================================================
class MapViewer(QGraphicsView):
    """
    Read-only map viewer that visualizes:
    - Background map image
    - Nodes
    - Directed paths
    - Traffic intensity using colors
    """

    # --------------------------------------------------------
    # Initialization
    # --------------------------------------------------------
    def __init__(self):
        super().__init__()

        # Scene setup
        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QColor(0, 0, 0))
        self.setScene(self.scene)

        # View settings
        self.setRenderHint(QPainter.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.ScrollHandDrag)

        # Load map data
        self.load_map()

    # ============================================================
    # Load Map Data
    # ============================================================
    def load_map(self):
        """
        Loads map data from JSON file and renders:
        - Background image
        - Nodes
        - Edges with traffic-based coloring
        """
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        # --------------------------------------------------------
        # Load background image
        # --------------------------------------------------------
        pixmap = QPixmap(data["image"])
        self.scene.addPixmap(pixmap)
        self.setSceneRect(self.scene.itemsBoundingRect())

        # --------------------------------------------------------
        # Draw nodes
        # --------------------------------------------------------
        for node_id, (x, y) in data["nodes"].items():
            node_id = int(node_id)
            pos = QPointF(x, y)

            node_item = QGraphicsEllipseItem(
                pos.x() - NODE_RADIUS,
                pos.y() - NODE_RADIUS,
                NODE_RADIUS * 2,
                NODE_RADIUS * 2,
            )

            node_item.setBrush(COLOR_NODE_NORMAL)

            pen = QPen(Qt.black)
            pen.setWidth(2)
            node_item.setPen(pen)

            node_item.setZValue(11)
            self.scene.addItem(node_item)

            # Node label
            label = QGraphicsTextItem(str(node_id))
            label.setDefaultTextColor(Qt.yellow)
            label.setPos(x + 4, y + 4)
            label.setZValue(10)
            self.scene.addItem(label)

        # --------------------------------------------------------
        # Draw edges
        # --------------------------------------------------------
        for edge in data["edges"]:
            points = [QPointF(p[0], p[1]) for p in edge["points"]]

            # Build path geometry
            path = QPainterPath(points[0])
            for p in points[1:]:
                path.lineTo(p)

            # Edge outline (background)
            outline_pen = QPen(COLOR_PATH_OUTLINE, 11)
            outline_pen.setCapStyle(Qt.RoundCap)
            outline_pen.setJoinStyle(Qt.RoundJoin)

            outline_item = self.scene.addPath(path, outline_pen)
            outline_item.setZValue(4)

            # Determine color based on traffic
            traffic_value = edge.get("traffic", 1.0)
            path_color = self.get_traffic_color(traffic_value)

            # Main edge path
            main_pen = QPen(path_color, 6)
            main_pen.setCapStyle(Qt.RoundCap)
            main_pen.setJoinStyle(Qt.RoundJoin)

            main_item = self.scene.addPath(path, main_pen)
            main_item.setZValue(5)

        print("✅ Map loaded successfully")

    # ============================================================
    # Traffic Color Mapping
    # ============================================================
    def get_traffic_color(self, traffic):
        """
        Safely converts traffic value to float and maps it to a color.
        """
        try:
            traffic = float(traffic)
        except (ValueError, TypeError):
            traffic = 1.0  # fallback

        if traffic < 3.5:
            return COLOR_PATH_TRAFFIC_GREEN
        elif traffic < 6.5:
            return COLOR_PATH_TRAFFIC_ORANGE
        else:
            return COLOR_PATH_TRAFFIC_RED


    # ============================================================
    # Zoom Handling
    # ============================================================
    def wheelEvent(self, event):
        """
        Zoom in/out using mouse wheel.
        """
        zoom_factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        self.scale(zoom_factor, zoom_factor)


# ============================================================
# Application Entry Point
# ============================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = MapViewer()
    viewer.resize(1000, 800)
    viewer.show()
    sys.exit(app.exec_())

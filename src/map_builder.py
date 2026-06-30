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
    QInputDialog,
    QGraphicsRectItem,
)
from PyQt5.QtGui import (
    QPen,
    QPainterPath,
    QPixmap,
    QPainter,
    QColor,
    QFont,
)
from PyQt5.QtCore import Qt, QPointF


# ============================================================
# Configuration
# ============================================================
IMAGE_PATH = r"assets/map3.png"
MAX_NODES = 30
NODE_RADIUS = 6
NODE_DETECT = 30
MIN_DIST = 10

COLOR_NODE_NORMAL = QColor(190, 0, 50)

COLOR_PATH_MAIN = QColor(255, 255, 255, 220)
COLOR_PATH_OUTLINE = QColor(70, 70, 70, 200)

# Traffic colors
COLOR_PATH_TRAFFIC_GREEN = QColor(0, 200, 0)  # low traffic (grren)
COLOR_PATH_TRAFFIC_ORANGE = QColor(255, 165, 0)  # mid traffic (orange)
COLOR_PATH_TRAFFIC_RED = QColor(255, 0, 0)  # high traffic (red)


# ============================================================
# Map Editor
# ============================================================
class MapEditor(QGraphicsView):
    def __init__(self):
        super().__init__()

        # ---------------- Scene ----------------
        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QColor(0, 0, 0))  
        self.setScene(self.scene)
        
        # ---------------- Load map ----------------
        pixmap = QPixmap(IMAGE_PATH)
        self.map_item = self.scene.addPixmap(pixmap)
        self.setSceneRect(self.scene.itemsBoundingRect())

        # ---------------- Data ----------------
        self.nodes = {}   # id -> {pos, item}
        self.edges = []   # list of edges
        self.mode = "node"
        self.drawing = False

        self.path = None
        self.path_item = None
        self.path_outline = None
        self.path_points = []

        self.start_node = None
        self.traffic_mode = False 

        # ---------------- View ----------------
        self.setRenderHint(QPainter.Antialiasing)
        self.update_drag_mode()
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setFocusPolicy(Qt.StrongFocus)
        self.create_help_bar()
        self.setFocus()

        print("MODE: NODE")

    # ========================================================
    # Utilities
    # ========================================================
    def find_node(self, pos, radius=15):
        for i, data in self.nodes.items():
            if (data["pos"] - pos).manhattanLength() <= radius:
                return i
        return None
    
    def update_drag_mode(self):
        if self.mode == "node":
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        else:
            self.setDragMode(QGraphicsView.NoDrag)

    def path_length(self, points):
        total = 0.0
        for i in range(1, len(points)):
            dx = points[i].x() - points[i-1].x()
            dy = points[i].y() - points[i-1].y()
            total += (dx*dx + dy*dy) ** 0.5
        return total

    def cancel_path(self):
        if self.path_item:
            self.scene.removeItem(self.path_item)
        if hasattr(self, "path_outline") and self.path_outline:
            self.scene.removeItem(self.path_outline)

        self.start_node = None
        self.drawing = False
        self.path = None
        self.path_item = None
        self.path_outline = None
        self.path_points = []

        print("❌ Path canceled")

    def save_all(self):
        with open("data/map_data.json", "w", encoding="utf-8") as f:
            json.dump({
                "image": IMAGE_PATH,
                "nodes": {k: (v["pos"].x(), v["pos"].y()) for k, v in self.nodes.items()},
                "edges": [
                    {k: e[k] for k in e if k not in ("item", "outline")}
                    for e in self.edges
                ]
            }, f, indent=2)

        with open("log.txt", "w", encoding="utf-8") as f:
            f.write("NODES:\n")
            for k, v in self.nodes.items():
                f.write(f"{k}: {v['pos'].x()}, {v['pos'].y()}\n")

            f.write("\nEDGES:\n")
            for e in self.edges:
                f.write(str(e) + "\n")

        print("Saved map_data.json & log.txt")

    # ========================================================
    # Traffic
    # ========================================================
    def get_traffic(self):
        # Request traffic value from the user
        traffic, ok = QInputDialog.getDouble(self, "Traffic", "Enter traffic value (0-10):", 1.0, 0, 10, 1)
        if ok:
            return traffic
        else:
            return 1.0  # Default traffic value

    def start_traffic_input_mode(self):
        # Enable traffic input mode
        self.traffic_mode = True
        print("Traffic input mode activated. Please draw a path first and then enter traffic.")

    def get_traffic_color(self, traffic):
        # CHANGE COLOE OF PATH BASED ON TRAFFIC
        if traffic <= 3.5:
            return COLOR_PATH_TRAFFIC_GREEN
        elif traffic <= 6.5:
            return COLOR_PATH_TRAFFIC_ORANGE
        else:
            return COLOR_PATH_TRAFFIC_RED

    # ========================================================
    # Mouse Events
    # ========================================================
    def mousePressEvent(self, event):
        pos = self.mapToScene(event.pos())
        node = self.find_node(pos, NODE_DETECT)

        if self.traffic_mode:
            # In traffic input mode, ask for traffic value
            traffic = self.get_traffic()
            self.traffic_mode = False  # Disable traffic mode after input

            # Find the last added edge and set its traffic value
            if self.edges:
                self.edges[-1]['traffic'] = traffic
                print(f"Traffic for last path: {traffic}")
            self.drawing = False  # Ensure drawing is reset after traffic input
            return  # Exit early as we do not want to process further in traffic mode
        

        # -------- Node mode --------
        if self.mode == "node" and event.button() == Qt.LeftButton:
            super().mousePressEvent(event)
            return
        
        pos = self.mapToScene(event.pos())

        if self.mode == "node" and event.button() == Qt.RightButton:
            if len(self.nodes) >= MAX_NODES:
                print(f"❌ MAX NODES reached ({MAX_NODES})")
                return
            idx = len(self.nodes)
            
            circle = QGraphicsEllipseItem(
            pos.x() - NODE_RADIUS,
            pos.y() - NODE_RADIUS,
            NODE_RADIUS * 2,
            NODE_RADIUS * 2
            )

            circle.setBrush(COLOR_NODE_NORMAL)
            pen = QPen(Qt.white)
            pen.setWidth(1)        
            circle.setPen(pen)
            circle.setZValue(11)
            self.scene.addItem(circle)


            label = QGraphicsTextItem(str(idx))
            label.setDefaultTextColor(Qt.yellow)
            label.setPos(pos.x() + 4, pos.y() + 4)
            label.setZValue(10)
            self.scene.addItem(label)

            self.nodes[idx] = {
                "pos": pos,
                "item": circle,
                "label": label
            }

        # -------- Path mode --------
        elif self.mode == "path" and event.button() == Qt.LeftButton:
            node = self.find_node(pos, NODE_DETECT)

            if self.start_node is None:
                if node is None:
                    print("❌ click on start node")
                    return
                self.start_node = node
                self.drawing = True
                self.path_points = [self.nodes[node]["pos"]]
                self.path = QPainterPath(self.nodes[node]["pos"])

                outline_pen = QPen(QColor(70, 70, 70, 195), 12)
                outline_pen.setCapStyle(Qt.RoundCap)
                outline_pen.setJoinStyle(Qt.RoundJoin)
                self.path_outline = self.scene.addPath(self.path, outline_pen)
                self.path_outline.setZValue(4)

                # main path
                main_pen = QPen(QColor(255, 255, 255, 220), 6)
                main_pen.setCapStyle(Qt.RoundCap)
                main_pen.setJoinStyle(Qt.RoundJoin)
                self.path_item = self.scene.addPath(self.path, main_pen)
                
                self.path_item.setZValue(5)
                print(f"Start node: {node}")

            else:
                if node is not None and node != self.start_node:
                    # snap to end node
                    end_pos = self.nodes[node]["pos"]
                    self.path.lineTo(end_pos)
                    self.path_points.append(end_pos)

                    length = self.path_length(self.path_points)
                    traffic = 1.0  # Default traffic if not set yet

                    traffic = self.get_traffic()

                    edge = {
                        "from": self.start_node,
                        "to": node,
                        "points": [(p.x(), p.y()) for p in self.path_points],
                        "length": length,
                        "traffic": traffic,
                        "cost": length * traffic,
                        "item": self.path_item,          # Main path
                        "outline": self.path_outline     # Outline of the path
                    }

                    self.edges.append(edge)
                    print(f"Path saved: {self.start_node} -> {node} | "
                            f"length = {length:.1f}, traffic = {traffic}, cost = {length * traffic:.1f}")

                # reset state
                self.start_node = None
                self.drawing = False
                self.path = None
                self.path_item = None
                self.path_points = []

        super().mousePressEvent(event)
        
    # ============================================================
    # Help Bar (UI Overlay)
    # ============================================================
    def create_help_bar(self):
        padding_x = 24
        padding_y = 14

        text = (
            "N : Node Mode   |   "
            "Right Click : Insert Nodes  |   "
            "P : Path Mode   |   "
            "Escape : Cancel The Path   |   "
            "Q : Save & Exit"
        )

        self.help_text = QGraphicsTextItem(text)
        self.help_text.setFont(QFont("Arial", 11, QFont.Bold))
        self.help_text.setDefaultTextColor(Qt.white)
        self.help_text.setZValue(1001)

        text_rect = self.help_text.boundingRect()

        self.help_bar = QGraphicsRectItem(
            0, 0,
            text_rect.width() + padding_x * 2,
            text_rect.height() + padding_y * 2
        )
        self.help_bar.setBrush(QColor(20, 30, 60))
        self.help_bar.setPen(QPen(Qt.white, 2))
        self.help_bar.setZValue(1000)

        self.scene.addItem(self.help_bar)
        self.scene.addItem(self.help_text)

        self.help_text.setPos(
            self.help_bar.rect().width() / 2 - text_rect.width() / 2,
            self.help_bar.rect().height() / 2 - text_rect.height() / 2
        )

        map_center = self.map_item.boundingRect().center()

        self.help_bar.setPos(
            map_center.x() - self.help_bar.rect().width() / 2,
            map_center.y() - self.help_bar.rect().height() / 2
        )

        self.help_text.moveBy(
            self.help_bar.pos().x(),
            self.help_bar.pos().y()
        )



    def resizeEvent(self, event):
        super().resizeEvent(event)

        if hasattr(self, "help_bar"):
            view_width = self.viewport().width()
            bar_width = self.help_bar.rect().width()

            x = (view_width - bar_width) / 2
            self.help_bar.setPos(x, 10)

            text_rect = self.help_text.boundingRect()
            self.help_text.setPos(
                x + self.help_bar.rect().width() / 2 - text_rect.width() / 2,
                10 + self.help_bar.rect().height() / 2 - text_rect.height() / 2
            )



    # ========================================================
    # Mouse Move
    # ========================================================
    def mouseMoveEvent(self, event):
        pos = self.mapToScene(event.pos())

        if self.drawing and self.mode == "path":
            pos = self.mapToScene(event.pos())

            last = self.path_points[-1]
            if (pos - last).manhattanLength() < MIN_DIST:
                return  # remove jitter

            self.path.lineTo(pos)
            self.path_outline.setPath(self.path)
            self.path_item.setPath(self.path)

            self.path_points.append(pos)

        super().mouseMoveEvent(event)


    # ========================================================
    # Zoom
    # ========================================================
    def wheelEvent(self, event):
        zoom_factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        self.scale(zoom_factor, zoom_factor)


    # ========================================================
    # Keyboard
    # ========================================================
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_N:
            self.mode = "node"
            self.update_drag_mode()
            self.drawing = False
            print("MODE: NODE")

        elif event.key() == Qt.Key_P:
            if len(self.nodes) < 2:
                print("Add nodes first")
                return
            self.mode = "path"
            print("MODE: PATH")

        elif event.key() == Qt.Key_Q:
            self.save_all()
            QApplication.quit()

        elif event.key() == Qt.Key_Escape:
            if self.drawing:
                self.cancel_path()

        elif event.key() == Qt.Key_T:
            self.start_traffic_input_mode()


# ============================================================
# Run
# ============================================================
app = QApplication(sys.argv)
w = MapEditor()
w.resize(1000, 800)
w.show()
sys.exit(app.exec_())

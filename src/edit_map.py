import sys, json
from PyQt5.QtWidgets import (
    QApplication, QGraphicsView, QGraphicsScene,
    QGraphicsEllipseItem, QGraphicsTextItem, QInputDialog
)
from PyQt5.QtGui import QPen, QPainterPath, QPixmap, QPainter
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QColor

# -------- CONFIG --------
IMAGE_PATH = r"assets/map3.png"
DATA_PATH = r"data/map_data.json"
MAX_NODES = 30
NODE_RADIUS = 6
NODE_DETECT = 30
MIN_DIST = 10

COLOR_NODE_NORMAL = QColor(190, 0, 50)
COLOR_PATH_MAIN = QColor(255, 255, 255, 220)
COLOR_PATH_OUTLINE = QColor(70, 70, 70, 200)

#colors for traffic
COLOR_PATH_TRAFFIC_GREEN = QColor(0, 200, 0)  # low traffic (grren)
COLOR_PATH_TRAFFIC_ORANGE = QColor(255, 165, 0)  # mid traffic (orange)
COLOR_PATH_TRAFFIC_RED = QColor(255, 0, 0)  # high traffic (red)


class MapEditor(QGraphicsView):
    def __init__(self):
        super().__init__()

        # ---- scene ----
        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QColor(0, 0, 0))  
        self.setScene(self.scene)
        
        # ---- load map ----
        pixmap = QPixmap(IMAGE_PATH)
        self.scene.addPixmap(pixmap)
        self.setSceneRect(self.scene.itemsBoundingRect())

        # ---- data ----
        self.nodes = {}   # id -> {pos, item}
        self.edges = []   # list of edges
        self.mode = "node"
        self.drawing = False
        self.path = None
        self.path_item = None
        self.path_points = []
        self.start_node = None
        self.traffic_mode = False  # Flag to check if in traffic input mode

        # ---- view ----
        self.setRenderHint(QPainter.Antialiasing)
        self.update_drag_mode()
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()

        print("MODE: NODE")

        self.load_from_json()  # Load the map and paths, but no new nodes should be added

    # ---------- LOAD ----------
    def load_from_json(self):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Load nodes if they already exist in the map data
        for k, (x, y) in data["nodes"].items():
            k = int(k)
            pos = QPointF(x, y)

            c = QGraphicsEllipseItem(
                x - NODE_RADIUS, y - NODE_RADIUS,
                NODE_RADIUS * 2, NODE_RADIUS * 2
            )
            c.setBrush(COLOR_NODE_NORMAL)
            c.setPen(QPen(Qt.white, 1))  # Set the white border for nodes
            c.setZValue(10)
            self.scene.addItem(c)

            t = QGraphicsTextItem(str(k))
            t.setDefaultTextColor(Qt.yellow)
            t.setPos(x + 4, y + 4)
            t.setZValue(10)
            self.scene.addItem(t)

            self.nodes[k] = {"pos": pos, "item": c}

        # Load paths (edges)
        for e in data["edges"]:
            e["from"] = int(e["from"])
            e["to"] = int(e["to"])

            path = QPainterPath()

            pts = [QPointF(p[0], p[1]) for p in e["points"]]
            path.moveTo(pts[0])
            for p in pts[1:]:
                path.lineTo(p)

            outline = self.scene.addPath(path, QPen(QColor(70, 70, 70), 11))
            main = self.scene.addPath(path, QPen(QColor(255, 255, 255), 6))
            outline.setZValue(4)
            main.setZValue(5)

            e["item"] = main
            e["outline"] = outline
            self.edges.append(e)

    # ---------- utils ----------
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
        with open(DATA_PATH, "w", encoding="utf-8") as f:
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
    
    # ---------- get traffic ----------
    def get_traffic(self):
        traffic, ok = QInputDialog.getDouble(self, "Traffic", "Enter traffic value (0-10):", 1.0, 0, 10, 1)
        if ok:
            return traffic
        else:
            return 1.0  # Default traffic value

    def start_traffic_input_mode(self):
        self.traffic_mode = True
        print("Traffic input mode activated. Please draw a path first and then enter traffic.")

    def get_traffic_color(self, traffic):
        if traffic <= 3.5:
            return COLOR_PATH_TRAFFIC_GREEN
        elif traffic <= 6.5:
            return COLOR_PATH_TRAFFIC_ORANGE
        else:
            return COLOR_PATH_TRAFFIC_RED

    # ---------- mouse ----------    
    def mousePressEvent(self, event):
        pos = self.mapToScene(event.pos())
        node = self.find_node(pos, NODE_DETECT)

        if self.traffic_mode:
            traffic = self.get_traffic()
            self.traffic_mode = False

            if self.edges:
                self.edges[-1]['traffic'] = traffic
                print(f"Traffic for last path: {traffic}")
            self.drawing = False
            return
        
        # Only allow adding paths
        if self.mode == "path" and event.button() == Qt.LeftButton:
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

                main_pen = QPen(QColor(255, 255, 255, 220), 6)
                main_pen.setCapStyle(Qt.RoundCap)
                main_pen.setJoinStyle(Qt.RoundJoin)
                self.path_item = self.scene.addPath(self.path, main_pen)
                
                self.path_item.setZValue(5)
                print(f"Start node: {node}")

            else:
                if node is not None and node != self.start_node:
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
                        "item": self.path_item,          
                        "outline": self.path_outline     
                    }

                    self.edges.append(edge)
                    print(f"Path saved: {self.start_node} -> {node} | length = {length:.1f}, traffic = {traffic}, cost = {length * traffic:.1f}")

                self.start_node = None
                self.drawing = False
                self.path = None
                self.path_item = None
                self.path_points = []

        super().mousePressEvent(event)

    # ---------- move ----------
    def mouseMoveEvent(self, event):
        pos = self.mapToScene(event.pos())

        if self.drawing and self.mode == "path":
            last = self.path_points[-1]
            if (pos - last).manhattanLength() < MIN_DIST:
                return  # remove jitter

            self.path.lineTo(pos)
            self.path_outline.setPath(self.path)
            self.path_item.setPath(self.path)

            self.path_points.append(pos)

        super().mouseMoveEvent(event)

    # ---------- zoom ----------
    def wheelEvent(self, event):
        zoom_factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        self.scale(zoom_factor, zoom_factor)

    # ---------- keyboard ----------
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_N:
            print("Adding nodes is disabled.")
            return  # Don't allow adding new nodes in this mode.

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


# ---------- run ----------
app = QApplication(sys.argv)
w = MapEditor()
w.resize(1000, 800)
w.show()
sys.exit(app.exec_())

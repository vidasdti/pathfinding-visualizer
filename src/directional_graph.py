# ============================================================
# Imports
# ============================================================
import sys
import json
import heapq
import math
from collections import deque

from PyQt5.QtWidgets import (
    QApplication,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsEllipseItem,
    QGraphicsTextItem,
    QInputDialog,
    QGraphicsPathItem,
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
from PyQt5.QtCore import Qt, QPointF, QTimer


# ============================================================
# Configuration Constants
# ============================================================
IMAGE_PATH = r"assets/map3.png"

NODE_RADIUS = 6            # Radius of each node circle
NODE_DETECT = 30           # Mouse detection radius for selecting nodes

# Node colors
COLOR_NODE_NORMAL = QColor(190, 0, 50)
COLOR_NODE_HOVER = QColor(255, 165, 0)
COLOR_NODE_START = QColor(0, 200, 0)
COLOR_NODE_GOAL = QColor(70, 130, 255)

class AlgorithmItem(QGraphicsTextItem):
    def __init__(self, name, index, editor):
        super().__init__(name)
        self.name = name
        self.index = index
        self.editor = editor

        self.setFont(QFont("Arial", 12))
        self.setDefaultTextColor(Qt.white)
        self.setAcceptHoverEvents(True)

    def hoverEnterEvent(self, event):
        self.editor.alg_index = self.index
        self.editor.update_algorithm_highlight()
        super().hoverEnterEvent(event)

    def mousePressEvent(self, event):
        self.editor.current_algorithm = self.name
        print(f"✅ Algorithm set to {self.name}")
        self.editor.hide_algorithm_menu()
        event.accept()

# ============================================================
# Direction Arrow Graphics Item
# ============================================================
class DirectionArrow(QGraphicsPathItem):
    """
    Graphical arrow used to show direction of edges.
    """

    def __init__(self, length=28, head=10):
        super().__init__()

        path = QPainterPath()

        # Arrow shaft (main body)
        path.moveTo(-length, 0)
        path.lineTo(0, 0)

        # Arrow head
        path.moveTo(0, 0)
        path.lineTo(-head, -head / 2)
        path.moveTo(0, 0)
        path.lineTo(-head, head / 2)

        self.setPath(path)

        # Outer black outline (thicker)
        self.setPen(QPen(QColor(0, 0, 0), 6, Qt.SolidLine, Qt.RoundCap))
        self.setZValue(20)

        # Inner colored arrow (visual highlight)
        inner = QGraphicsPathItem(path, self)
        inner.setPen(QPen(QColor(255, 215, 0), 2.5, Qt.SolidLine, Qt.RoundCap))
        inner.setZValue(21)


# ============================================================
# Main Map Editor Class
# ============================================================
class MapEditor(QGraphicsView):
    """
    Interactive map editor and pathfinding visualizer.
    Supports BFS, DFS, UCS, and A* algorithms.
    """

    # --------------------------------------------------------
    # Initialization
    # --------------------------------------------------------
    def __init__(self):
        super().__init__()

        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QColor(0, 0, 0))  
        self.setScene(self.scene)

        # Load background map image
        pixmap = QPixmap(IMAGE_PATH)
        self.map_item = self.scene.addPixmap(pixmap)
        self.setSceneRect(self.scene.itemsBoundingRect())
        
        # Data containers
        self.direction_marks = []   # Direction arrows
        self.nodes = {}             # Node data
        self.edges = []             # Edge data

        # State variables
        self.start_node = None
        self.goal_node = None
        self.drag_enabled = False
        self.setDragMode(QGraphicsView.NoDrag)

        self.selecting_start = False
        self.selecting_goal = False

        self.current_algorithm = "UCS"

        # Animation control
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_step)
        self.steps = []
        self.step = 0
        self.best_path = None
        self.is_ucs_running = False
        self.alg_menu = None
        self.alg_items = []
        self.algorithms = ["UCS", "BFS", "DFS", "A*"]
        self.alg_index = 0


        # View settings
        self.setRenderHint(QPainter.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Load map data and UI
        self.load_from_json()
        print("✅ Map loaded. Press A to select algorithm.")
        self.create_help_bar()
        self.color_edges_by_traffic()

        # Arrow blinking control
        self.blink_state = True
        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.blink_arrows)
        self.blink_on = True
        self.blink_timer.start(300)  

        self.setFocus()

    # ============================================================
    # Load Nodes and Edges from JSON
    # ============================================================
    def load_from_json(self):
        """
        Loads nodes and edges from map_data.json and renders them.
        """
        with open("data/map_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        for k, (x, y) in data["nodes"].items():
            k = int(k)
            pos = QPointF(x, y)

            c = QGraphicsEllipseItem(
                x - NODE_RADIUS, y - NODE_RADIUS,
                NODE_RADIUS * 2, NODE_RADIUS * 2
            )
            c.setBrush(COLOR_NODE_NORMAL)
            c.setPen(QPen(Qt.white, 1.5))
            c.setZValue(10)
            self.scene.addItem(c)

            t = QGraphicsTextItem(str(k))
            t.setDefaultTextColor(Qt.yellow)
            t.setPos(x + 4, y + 4)
            t.setZValue(10)
            self.scene.addItem(t)

            self.nodes[k] = {"pos": pos, "item": c}


        # Load edges
        for e in data["edges"]:
            e["from"] = int(e["from"])
            e["to"] = int(e["to"])

            path = QPainterPath()
            pts = [QPointF(p[0], p[1]) for p in e["points"]]

            path.moveTo(pts[0])
            for p in pts[1:]:
                path.lineTo(p)

            # Edge outline (background)
            outline = self.scene.addPath(path, QPen(QColor(70, 70, 70), 11))
            # Edge main path
            main = self.scene.addPath(path, QPen(QColor(255, 255, 255), 6))
            
            outline.setZValue(4)
            main.setZValue(5)

            e["item"] = main
            e["outline"] = outline
            self.edges.append(e)


    # ============================================================
    # Graph Construction
    # ============================================================
    def build_graph(self):
        """
        Builds adjacency list representation of the directed graph.
        """
        g = {}
        for e in self.edges:
            g.setdefault(e["from"], []).append((e["to"], e))
        return g

    # ============================================================
    # Edge Information
    # ============================================================
    def edge_info(self, a, b):
        """
        Returns (length, traffic, cost) for edge a -> b.
        """
        for e in self.edges:
            if e["from"] == a and e["to"] == b:
                length = e["length"]        
                traffic = e.get("traffic", 0)
                cost = length * (1 + traffic/10)
                return length, traffic, cost

        return 0, 0, float("inf")
    
    # ============================================================
    # Search Cost Selection (BFS / DFS vs UCS / A*)
    # ============================================================
    def edge_cost_for_paths(self, a, b):
        """
        Returns edge cost based on selected algorithm.
        - BFS / DFS : use only geometric length
        - UCS / A*  : use weighted cost (length + traffic)
        """
        length, traffic, cost = self.edge_info(a, b)

        if self.current_algorithm in ["BFS", "DFS"]:
            return length

        return cost

    # ============================================================
    # Find All Possible Paths (Analysis / Explanation Only)
    # ============================================================
    def find_all_paths(self, start, goal, limit=20):
        """
        Finds all possible paths from start to goal using DFS.
        Used only for explanation and comparison.
        """
        graph = self.build_graph()
        all_paths = []

        def dfs(n, path, total_cost):
            if len(all_paths) >= limit:
                return

            if n == goal:
                all_paths.append((path[:], total_cost))
                return

            for nxt, _ in graph.get(n, []):
                if nxt not in path:
                    c = self.edge_cost_for_paths(n, nxt)
                    dfs(nxt, path + [nxt], total_cost + c)

        dfs(start, [start], 0)
        return all_paths
    
    # ============================================================
    # Algorithm Selection Overlay
    # ============================================================
    def show_algorithm_menu(self):
        if self.alg_menu:
            return

        width = 300
        height = 220

        center = self.map_item.boundingRect().center()

        self.alg_menu = QGraphicsRectItem(0, 0, width, height)
        self.alg_menu.setBrush(QColor(30, 30, 60))
        self.alg_menu.setPen(QPen(Qt.white, 2))
        self.alg_menu.setZValue(2000)

        self.alg_menu.setPos(
            center.x() - width / 2,
            center.y() - height / 2
        )

        self.scene.addItem(self.alg_menu)

        title = QGraphicsTextItem("Select Algorithm")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setDefaultTextColor(QColor(255, 200, 220))
        title.setZValue(2001)
        title.setParentItem(self.alg_menu)

        # --- CENTER TITLE ---
        title_rect = title.boundingRect()
        title_x = (width - title_rect.width()) / 2
        title.setPos(title_x, 15)


        self.alg_items = []
        y = 60

        for i, name in enumerate(self.algorithms):
            t = AlgorithmItem(name, i, self)
            t.setZValue(2001)
            t.setParentItem(self.alg_menu)
            text_rect = t.boundingRect()
            x = (width - text_rect.width()) / 2
            t.setPos(x, y)

            self.alg_items.append(t)
            y += 35

        self.alg_index = self.algorithms.index(self.current_algorithm)
        self.update_algorithm_highlight()


    def update_algorithm_highlight(self):
        for i, t in enumerate(self.alg_items):
            if i == self.alg_index:
                t.setDefaultTextColor(QColor(90, 170, 255))
                t.setFont(QFont("Arial", 12, QFont.Bold))
            else:
                t.setDefaultTextColor(Qt.white)
                t.setFont(QFont("Arial", 12))
    
    def hide_algorithm_menu(self):
        if self.alg_menu:
            self.scene.removeItem(self.alg_menu)
            self.alg_menu = None
            self.alg_items = []
    
    # ============================================================
    # Breadth-First Search (BFS)
    # ============================================================
    def bfs(self, start, goal):
        """
        Breadth-First Search.
        Ignores weights and traffic, explores level by level.
        """
        q = deque([(start, [start])])
        vis = set()
        self.steps = []

        graph = self.build_graph()

        while q:
            n, path = q.popleft()

            if n in vis:
                continue
            vis.add(n)

            # Visualization step
            self.steps.append((path, False))

            if n == goal:
                self.best_path = path
                self.steps.append((path, True))
                return

            for nxt, _ in graph.get(n, []):
                if nxt not in vis:
                    q.append((nxt, path + [nxt]))

    # ============================================================
    # Depth-First Search (DFS)
    # ============================================================
    def dfs(self, start, goal):
        """
        Depth-First Search.
        Explores as deep as possible before backtracking.
        """
        stack = [(start, [start])]
        vis = set()
        self.steps = []

        graph = self.build_graph()

        while stack:
            n, path = stack.pop()

            if n in vis:
                continue
            vis.add(n)

            self.steps.append((path, False))

            if n == goal:
                self.best_path = path
                self.steps.append((path, True))
                return

            for nxt, _ in graph.get(n, []):
                if nxt not in vis:
                    stack.append((nxt, path + [nxt]))


    # ============================================================
    # A* Search Algorithm
    # ============================================================
    def astar(self, start, goal):
        def h(n):
            return (self.nodes[n]["pos"] - self.nodes[goal]["pos"]).manhattanLength()

        pq = [(h(start), 0, start, [start])]
        seen = {}
        self.steps = []

        graph = self.build_graph()

        while pq:
            _, cost, n, path = heapq.heappop(pq)

            if n in seen and seen[n] <= cost:
                continue
            seen[n] = cost

            self.steps.append((path, False))

            if n == goal:
                self.best_path = path
                self.steps.append((path, True))
                return

            for nxt, e in graph.get(n, []):
                length = e["length"]
                traffic = e.get("traffic", 0)

                edge_cost = length * (1 + traffic/10)   # real cost

                g2 = cost + edge_cost
                f2 = g2 + h(nxt)

                heapq.heappush(pq, (f2, g2, nxt, path + [nxt]))

    # ============================================================
    # Uniform Cost Search (UCS) - Visual Version
    # ============================================================
    def ucs(self, start, goal):
        """
        Uniform Cost Search.
        Expands lowest cumulative cost first.
        """
        pq = [(0, start, [start])]
        visited = {}

        self.steps = []
        graph = self.build_graph()

        # Prune nodes that cannot reach the goal
        can_reach_goal = self.nodes_that_can_reach_goal(goal)

        if start not in can_reach_goal:
            return False

        while pq:
            cost, node, path = heapq.heappop(pq)

            if node in visited and visited[node] <= cost:
                continue

            visited[node] = cost
            self.steps.append((path, False))

            if node == goal:
                self.best_path = path
                self.steps.append((path, True))
                return True

            for nxt, e in graph.get(node, []):

                if nxt not in can_reach_goal:
                    continue

                length = e["length"]
                traffic = e.get("traffic", 0)
                edge_cost = length * (1 + traffic / 10)

                heapq.heappush(
                    pq,
                    (cost + edge_cost, nxt, path + [nxt])
                )

        return False

    # ============================================================
    # Nodes That Can Reach Goal (Reverse Graph Pruning)
    # ============================================================
    def nodes_that_can_reach_goal(self, goal):
        """
        Returns set of nodes that have a path to the goal.
        Used to prune UCS search space.
        """
        rev = {}

        for e in self.edges:
            rev.setdefault(e["to"], []).append(e["from"])

        reachable = set()
        stack = [goal]

        while stack:
            n = stack.pop()
            if n in reachable:
                continue

            reachable.add(n)
            for prev in rev.get(n, []):
                stack.append(prev)

        return reachable

    # ============================================================
    # Animation Control
    # ============================================================
    def next_step(self):
        """
        Animates algorithm exploration step-by-step.
        """
        if self.step < len(self.steps):
            p, fin = self.steps[self.step]
            self.highlight(p)
            if fin:
                self.best_path = p
                self.show_best()
                self.explain_path()
            self.step += 1

        else:
            self.timer.stop()

    # ============================================================
    # Path Visualization
    # ============================================================

    def highlight(self, path):
        """
        Highlights current exploration path.
        """
        for e in self.edges:
            e["item"].setPen(QPen(QColor(150, 150, 150), 4))

        for i in range(len(path) - 1):
            for e in self.edges:
                if e["from"] == path[i] and e["to"] == path[i + 1]:
                    e["item"].setPen(QPen(QColor(255, 140, 0), 5))

    def show_best(self):
        """
        Permanently highlights the optimal path.
        """
        if not self.best_path or len(self.best_path) < 2:
            print("❌ No path found")
            return

        for i in range(len(self.best_path) - 1):
            for e in self.edges:
                if (
                    (e["from"] == self.best_path[i] and e["to"] == self.best_path[i + 1])
                    ):

                    e["item"].setPen(QPen(QColor(0, 200, 0), 7))


    # ============================================================
    # Node Selection Helpers
    # ============================================================
    def find_node(self, pos):
        """
        Finds node under mouse cursor.
        """
        for i, n in self.nodes.items():
            if (n["pos"] - pos).manhattanLength() < NODE_DETECT:
                return i

    # ============================================================
    # Mouse Events
    # ============================================================
    def mousePressEvent(self, e):
        pos = self.mapToScene(e.pos())
        n = self.find_node(pos)

        if self.selecting_start and n is not None:
            self.start_node = n
            self.nodes[n]["item"].setBrush(COLOR_NODE_START)
            self.selecting_start = False

        elif self.selecting_goal and n is not None:
            self.goal_node = n
            self.nodes[n]["item"].setBrush(COLOR_NODE_GOAL)
            self.selecting_goal = False

        super().mousePressEvent(e)


    # ============================================================
    # Traffic-Based Edge Coloring
    # ============================================================
    def color_edges_by_traffic(self):
        """
        Colors edges based on traffic intensity.
        """
        for e in self.edges:
            traffic = e.get("traffic", 0)

            if 1 <= traffic < 3.5:
                color = QColor(0, 200, 0)      # green
            elif 3.5 <= traffic < 6.5:
                color = QColor(255, 165, 0)    # orange
            elif 6.5 <= traffic <= 10:
                color = QColor(220, 0, 0)      # red
            else:
                color = QColor(150, 150, 150)  # grey

            e["item"].setPen(QPen(color, 5))

    def reset_edges_gray(self):
        for e in self.edges:
            e["item"].setPen(QPen(QColor(150, 150, 150), 4))

    # ============================================================
    # Help Bar (UI Overlay)
    # ============================================================
    def create_help_bar(self):
        padding_x = 24
        padding_y = 14

        text = (
            "D : Drag   |   "
            "S : Select Start Node   |   "
            "G : Select Goal Node   |   "
            "A : Select Algorithm   |   "
            "R : Run Algorithm"
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


    # ============================================================
    # Direction Arrow Creation
    # ============================================================
    def draw_direction_marks(self):
        self.clear_direction_marks()

        for e in self.edges:
            pts = [QPointF(p[0], p[1]) for p in e["points"]]
            if len(pts) < 2:
                continue

            pos, angle = self.polyline_midpoint(pts)

            arrow = DirectionArrow(length=18, head=6)
            arrow.setRotation(angle)
            arrow.setPos(self.offset_point(pos, angle, dist=4))


            self.scene.addItem(arrow)
            self.direction_marks.append(arrow)
    

    def offset_point(self, pos, angle, dist=6):
        rad = math.radians(angle + 90)
        return QPointF(
            pos.x() + math.cos(rad) * dist,
            pos.y() + math.sin(rad) * dist
        )


    def blink_arrows(self):
        if self.blink_on:
           
            for a in self.direction_marks:
                a.setOpacity(0.0)

            self.blink_timer.start(400)
        else:
            for a in self.direction_marks:
                a.setOpacity(1.0)

            self.blink_timer.start(750) 

        self.blink_on = not self.blink_on

    
    def clear_direction_marks(self):
        for m in self.direction_marks:
            self.scene.removeItem(m)
        self.direction_marks.clear()


    def polyline_midpoint(self, pts):
        lengths = []
        total = 0

        for i in range(len(pts) - 1):
            l = math.hypot(
                pts[i+1].x() - pts[i].x(),
                pts[i+1].y() - pts[i].y()
            )
            lengths.append(l)
            total += l

        half = total / 2
        acc = 0

        for i, l in enumerate(lengths):
            if acc + l >= half:
                t = (half - acc) / l
                x = pts[i].x() + t * (pts[i+1].x() - pts[i].x())
                y = pts[i].y() + t * (pts[i+1].y() - pts[i].y())
                angle = math.degrees(math.atan2(
                    pts[i+1].y() - pts[i].y(),
                    pts[i+1].x() - pts[i].x()
                ))
                return QPointF(x, y), angle
            acc += l

        return pts[0], 0

        
    # ============================================================
    # PRINT OF EXPLAIN 
    # ============================================================
    def explain_path(self):
        if not self.best_path:
            return

        print("\n" + "=" * 50)
        print(f"🔍 Algorithm: {self.current_algorithm}")
        print(f"Start: {self.start_node} → Goal: {self.goal_node}")

        print("\nSelected Path:")
        print(" → ".join(map(str, self.best_path)))

        total_dist = 0
        total_traffic = 0
        total_cost = 0

        print("\nPath Details:")
        for i in range(len(self.best_path) - 1):
            a = self.best_path[i]
            b = self.best_path[i + 1]
            d, t, c = self.edge_info(a, b)

            total_dist += d
            total_traffic += t
            total_cost += c

            if self.current_algorithm in ["BFS", "DFS"]:
                print(f"{a} → {b} | distance = {d:.2f}")
            else:
                print(f"{a} → {b} | "f"distance = {d:.2f} | "f"traffic = {t:.2f} | "f"cost = {c:.2f}")


        print("\nTotals:")
        print(f"Distance   = {total_dist:.2f}")

        if self.current_algorithm in ["UCS", "A*"]:
            print(f"Traffic    = {total_traffic:.2f}")
            print(f"Total Cost = {total_cost:.2f}")


        # ---------- ALL POSSIBLE PATHS ----------
        print("\n📂 All possible paths from start to goal:")

        all_paths = self.find_all_paths(self.start_node, self.goal_node)

        # SORTED BY COST
        all_paths.sort(key=lambda x: x[1])

        for i, (p, c) in enumerate(all_paths, 1):
            print(f"{i:02d}) {' → '.join(map(str, p))} | cost = {c:.2f}")


        print("=" * 50 + "\n")


    # ============================================================
    # Mouse Drag Handling (Pan Map)
    # ============================================================

    def mouseMoveEvent(self, e):
        if self.selecting_start or self.selecting_goal:
            pos = self.mapToScene(e.pos())
            hovered = self.find_node(pos)

            for i, n in self.nodes.items():
                if i == hovered:
                    n["item"].setBrush(COLOR_NODE_HOVER)
                else:
                    if i == self.start_node:
                        n["item"].setBrush(COLOR_NODE_START)
                    elif i == self.goal_node:
                        n["item"].setBrush(COLOR_NODE_GOAL)
                    else:
                        n["item"].setBrush(COLOR_NODE_NORMAL)

        super().mouseMoveEvent(e)



    # ---------- zoom ----------
    def wheelEvent(self, event):
        zoom_factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        self.scale(zoom_factor, zoom_factor)

    # ============================================================
    # Keyboard Events
    # ============================================================
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_A:
            self.show_algorithm_menu()


        elif e.key() == Qt.Key_S:
            self.reset_edges_gray()
            self.selecting_start = True
            self.draw_direction_marks()

        elif e.key() == Qt.Key_G:
            self.selecting_goal = True

        elif e.key() == Qt.Key_R:
            if self.start_node is None or self.goal_node is None:
                print("❌ Select START and GOAL first")
                return

            self.step = 0
            self.steps = []
            self.best_path = None

            found = False

            if self.current_algorithm == "UCS":
                found = self.ucs(self.start_node, self.goal_node)
            elif self.current_algorithm == "BFS":
                self.bfs(self.start_node, self.goal_node)
                found = bool(self.best_path)
            elif self.current_algorithm == "DFS":
                self.dfs(self.start_node, self.goal_node)
                found = bool(self.best_path)
            else:
                self.astar(self.start_node, self.goal_node)
                found = bool(self.best_path)

            if not found:
                self.steps = []
                self.best_path = None
                print("❌ No path exists (graph is strictly directed)")
                return

            self.timer.start(400)
    

        elif e.key() == Qt.Key_D:
            self.drag_enabled = not self.drag_enabled

            if self.drag_enabled:
                self.setDragMode(QGraphicsView.ScrollHandDrag)
                print("✋ Drag ENABLED")
            else:
                self.setDragMode(QGraphicsView.NoDrag)
                print("🚫 Drag DISABLED")


        elif e.key() == Qt.Key_Q:
            QApplication.quit()


# ---------- RUN ----------
app = QApplication(sys.argv)
w = MapEditor()
w.resize(1000, 800)
w.show()
sys.exit(app.exec_())


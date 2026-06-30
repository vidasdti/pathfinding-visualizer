# Pathfinding Visualizer

An interactive Python application for visualizing classical graph search and pathfinding algorithms on a city-style map.

The project allows users to build graph-based road networks, assign traffic values to edges, and visualize how different algorithms explore and find paths between nodes.

---

# Features

- Interactive map editor
- BFS visualization
- DFS visualization
- Uniform Cost Search (UCS)
- A* Search Algorithm
- Directed and undirected graph support
- Traffic-based edge costs
- Animated path exploration
- Start/goal node selection
- Zoom and drag support
- Real-time path highlighting

---

# Project Components

The project consists of three main applications:

## Traffic Viewer

Displays the traffic map and traffic density visualization.

Run using:

```bash
python src/viewer.py
```

---

## Directed Graph Pathfinding

Interactive pathfinding visualization using directed graphs.

Supports:

- Algorithm selection
- Start/goal node selection
- Pathfinding execution
- Drag and zoom interaction

Run using:

```bash
python src/directional_graph.py
```

Controls:

| Key | Action |
|---|---|
| A | Select algorithm |
| S | Select start node |
| G | Select goal node |
| R | Run algorithm |
| D | Enable/disable drag |
| Mouse Wheel | Zoom |

---

## Undirected Graph Pathfinding

Interactive pathfinding visualization using undirected graphs.

Supports the same controls and interaction system as the directed graph version.

Run using:

```bash
python src/undirectional_graph.py
```

Controls:

| Key | Action |
|---|---|
| A | Select algorithm |
| S | Select start node |
| G | Select goal node |
| R | Run algorithm |
| D | Enable/disable drag |
| Mouse Wheel | Zoom |

---

# Algorithms

The project includes implementations of:

- Breadth-First Search (BFS)
- Depth-First Search (DFS)
- Uniform Cost Search (UCS)
- A* Search

Each algorithm can be visualized step-by-step directly on the map.

---

# Traffic Cost Model

Traffic values are assigned to edges and affect traversal cost.

The final edge cost is calculated using:

```text
Cost = Distance × (1 + Traffic / 10)
```

This cost model is used in:

- UCS
- A*

while BFS and DFS ignore weighted costs.

---

# Installation

Clone the repository:

```bash
git clone https://github.com/vidasdti/PythonProjects.git
cd PythonProjects/pathfinding-visualizer
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# Technologies Used

- Python
- PyQt5
- Graph Search Algorithms
- JSON
- Priority Queue (heapq)

---

# Presentation

A detailed presentation of the project is included in the repository.

- PDF version:
  `presentation/pathfinding-presentation.pdf`

---

"""
Triangle ordering for the GPU's post-transform vertex cache (#134).

Tom Forsyth's "Linear-Speed Vertex Cache Optimisation" (2006): each triangle
is emitted once, choosing the one whose vertices score highest. A vertex
scores by how recently it was used (so the next triangle reuses vertices still
in the cache) and by how few unemitted triangles still need it (so the mesh
is finished area by area, not left with scattered stragglers).

Pure Python, no Blender types, so it can be tested on its own.
"""
from typing import Dict, List, Sequence, Tuple

CACHE_SIZE = 32
CACHE_DECAY_POWER = 1.5
LAST_TRIANGLE_SCORE = 0.75
VALENCE_BOOST_SCALE = 2.0
VALENCE_BOOST_POWER = 0.5

Triangle = Tuple[int, int, int]


def _vertex_score(cache_position: int, remaining_triangles: int) -> float:
    if remaining_triangles == 0:
        return -1.0
    if cache_position < 0:
        score = 0.0
    elif cache_position < 3:
        # The last triangle's vertices: fine to reuse, but not so good that the
        # order degenerates into a fan around one vertex
        score = LAST_TRIANGLE_SCORE
    else:
        score = ((CACHE_SIZE - cache_position) / (CACHE_SIZE - 3)) ** CACHE_DECAY_POWER
    return score + VALENCE_BOOST_SCALE * remaining_triangles ** -VALENCE_BOOST_POWER


def optimize_triangle_order(triangles: Sequence[Triangle]) -> List[int]:
    """
    The indices of triangles in a cache-friendly order. Every triangle appears
    exactly once; each triangle's own corner order is unchanged
    """
    count = len(triangles)
    if count < 3:
        return list(range(count))

    remaining: Dict[int, int] = {}
    uses: Dict[int, List[int]] = {}
    for tri_index, triangle in enumerate(triangles):
        for vertex in triangle:
            remaining[vertex] = remaining.get(vertex, 0) + 1
            uses.setdefault(vertex, []).append(tri_index)

    cache_position = {vertex: -1 for vertex in remaining}
    vertex_scores = {
        vertex: _vertex_score(-1, remaining[vertex]) for vertex in remaining
    }
    triangle_scores = [
        sum(vertex_scores[vertex] for vertex in triangle) for triangle in triangles
    ]
    emitted = [False] * count
    cache: List[int] = []
    order: List[int] = []
    # Triangles not yet emitted, scanned when nothing in the cache suggests the next one
    pending = list(range(count))
    pending_scan = 0

    best = max(range(count), key=triangle_scores.__getitem__)
    while len(order) < count:
        if best < 0:
            # Nothing adjacent to the cache is left: start a new area with the
            # best remaining triangle, found by continuing the one scan of pending
            while emitted[pending[pending_scan]]:
                pending_scan += 1
            candidates = [t for t in pending[pending_scan : pending_scan + 64] if not emitted[t]]
            best = max(candidates, key=triangle_scores.__getitem__)

        order.append(best)
        emitted[best] = True
        for vertex in triangles[best]:
            remaining[vertex] -= 1

        # Move this triangle's vertices to the front of the cache, newest first
        front = list(triangles[best])
        cache = front + [vertex for vertex in cache if vertex not in front]
        for vertex in cache[CACHE_SIZE:]:
            cache_position[vertex] = -1
        del cache[CACHE_SIZE:]

        # Rescore the cached vertices and the triangles that still use them,
        # and choose the next triangle among those
        touched_triangles = set()
        for position, vertex in enumerate(cache):
            cache_position[vertex] = position
            vertex_scores[vertex] = _vertex_score(position, remaining[vertex])
            if remaining[vertex]:
                for tri_index in uses[vertex]:
                    if not emitted[tri_index]:
                        touched_triangles.add(tri_index)
        best = -1
        best_score = -1.0
        for tri_index in touched_triangles:
            score = sum(vertex_scores[vertex] for vertex in triangles[tri_index])
            triangle_scores[tri_index] = score
            if score > best_score:
                best, best_score = tri_index, score

    return order


def average_cache_miss_ratio(triangles: Sequence[Triangle], cache_size: int = CACHE_SIZE) -> float:
    """Cache misses per triangle for a FIFO cache: 3.0 is worst, about 0.5 is very good"""
    if not triangles:
        return 0.0
    fifo: List[int] = []
    misses = 0
    for triangle in triangles:
        for vertex in triangle:
            if vertex in fifo:
                continue
            misses += 1
            fifo.append(vertex)
            if len(fifo) > cache_size:
                fifo.pop(0)
    return misses / len(triangles)

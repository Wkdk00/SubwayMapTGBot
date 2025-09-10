import heapq

def min_time(graph, start, end):
    distances = {vertex: float('inf') for vertex in graph}
    distances[start] = 0

    priority_queue = [(0, start)]

    previous = {}

    while priority_queue:
        current_distance, current_vertex = heapq.heappop(priority_queue)

        if current_vertex == end:
            break

        if current_distance > distances[current_vertex]:
            continue

        for neighbor, weight in graph.get(current_vertex, []):
            distance = current_distance + weight

            if distance < distances[neighbor]:
                distances[neighbor] = distance
                previous[neighbor] = current_vertex
                heapq.heappush(priority_queue, (distance, neighbor))

    return distances[end], previous


def route(previous, start, end):
    path = []
    current = end

    while current != start:
        path.append(current)
        current = previous.get(current)
        if current is None:
            return []

    path.append(start)
    path.reverse()
    return path
from typing import Dict, Generic, List, Optional, Tuple, TypeVar

T = TypeVar('T')


class Graph(Generic[T]):
    def __init__(self,
                 adjacency_list: Dict[T,
                                      List[T]],
                 transpose: Optional['Graph'] = None):
        self.adjacency_list = adjacency_list
        self.__normalize_adjacency_list()
        if transpose is None:
            self._transpose = self.__compute_transpose()
        else:
            self._transpose = transpose

    def __normalize_adjacency_list(self):
        # Ensure that all vertices present in any adjacency list are
        # also keys in the adjacency list graph. If not, add them with
        # an empty adjacency list.
        vertices = set()
        for u in self.adjacency_list:
            vertices.add(u)
            for v in self.adjacency_list[u]:
                if v not in self.adjacency_list:
                    vertices.add(v)
        for u in vertices:
            if u not in self.adjacency_list:
                self.adjacency_list[u] = []

    def __compute_transpose(self) -> 'Graph':
        # Return a graph with the same set of vertices but where
        # the direction of all directed edges are reversed.
        transpose_adjacency_list = {}
        for u in self.adjacency_list.keys():
            transpose_adjacency_list[u] = []

        for u, lst in self.adjacency_list.items():
            for v in lst:
                transpose_adjacency_list[v].append(u)

        return Graph[T](transpose_adjacency_list, transpose=self)

    def transpose(self) -> 'Graph':
        return self._transpose

    def vertices(self) -> List[T]:
        # Return all the vertices in the graph
        return list(self.adjacency_list.keys())

    def edges(self) -> List[Tuple[T, T]]:
        # Return all the edges in the graph
        edges = []
        for u, lst in self.adjacency_list.items():
            for v in lst:
                edges.append((u, v))
        return edges

    def out_neighbors(self, v: T) -> List[T]:
        # Return the list of vertices u such that there
        # is an edge from v -> u
        return self.adjacency_list[v]

    def in_neighbors(self, v: T) -> List[T]:
        # Return the list of vertices u such that there
        # is an edge from u -> v
        return self._transpose.out_neighbors(v)

    def post_order(self) -> List[T]:
        # Return the vertices in a list sorted by post-order-traversal order.
        visited = dict.fromkeys(self.vertices(), False)
        post_order = []

        # Perform a depth first traversal of the graph rooted at
        # vertex v. Do not visit any vertices that have already
        # been visited.
        def visit(v):
            stack = [v]
            reversed_post_order = []
            while len(stack) != 0:
                v = stack[-1]
                stack.pop()
                if not visited[v]:
                    reversed_post_order.append(v)
                    visited[v] = True
                    for u in self.out_neighbors(v):
                        if not visited[u]:
                            stack.append(u)
            return reversed_post_order[::-1]
        # Perform a depth-first traversal rooted at each vertex to ensure
        # that all vertices are visited once.
        for v in self.vertices():
            post_order += visit(v)

        return post_order

    def strongly_connected_components(self) -> List[List[T]]:
        # Return a list of all strongly connected components in the
        # graph. Each component is represented as a list of all vertices
        # in the component.
        #
        # This is an implementation of Kosaraju's algorithm.
        # https://en.wikipedia.org/wiki/Kosaraju%27s_algorithm
        L = self.post_order()[::-1]
        component = dict.fromkeys(self.vertices(), None)

        # Assign each vertex reachable from v in the transpose graph
        # to component i if they have not already been assigned a component
        def assign(v, i):
            stack = [(v, i)]
            while len(stack) != 0:
                (v, i) = stack[-1]
                stack.pop()
                if component[v] is None:
                    component[v] = i
                    for u in self.in_neighbors(v):
                        if component[u] is None:
                            stack.append((u, i))

        for i, v in enumerate(L):
            assign(v, i)

        # Group all vertices by their assigned component.
        result = {}
        for v, r in component.items():
            if r in result:
                result[r].append(v)
            else:
                result[r] = [v]

        # Return a list of all strongly connected components.
        return list(result.values())

    def is_cyclical(self) -> bool:
        # return true if the graph is cyclical and false otherwise
        components = self.strongly_connected_components()
        for component in components:
            if len(component) != 1:
                return True
        return False

    def neighbor_gen(self, v) -> T:
        for k in self.adjacency_list[v]:
            yield k

    def topological_sort_helper(self, v, visited, stack):
        # iterative topological sort helper
        # working stack contains key and the corresponding current generator
        working_stack = [(v, self.neighbor_gen(v))]

        while working_stack:
            # get last element in stack
            v, gen = working_stack[-1]
            visited[v] = True

            # delete it from stack
            working_stack.pop()

            # run through neighbor generator until its empty
            continue_flag = True
            while continue_flag:
                next_neighbor = next(gen, None)

                # if generator has returned all neighbors
                if next_neighbor is None:
                    continue_flag = False
                    # Save current key into the result stack
                    stack.append(v)
                    continue

                # if new neighbor push current key and neighbor into stack
                if not visited[next_neighbor]:
                    working_stack.append((v, gen))
                    working_stack.append(
                        (next_neighbor, self.neighbor_gen(next_neighbor)))
                    continue_flag = False

    def topological_sort(self) -> List[T]:
        # Return a list of all vertices sorted topologically.
        # Note that a topological sort is only possible for graphs
        # without any directed cycles.
        if self.is_cyclical():
            raise RuntimeError(
                "topological sort is only possible for directed acylical graphs.")

        # Mark all the vertices as not visited
        visited = {}
        for v in self.vertices():
            visited[v] = False
        stack = []

        for key, value in visited.items():
            if not value:
                self.topological_sort_helper(key, visited, stack)

        return stack[::-1]

    def reachable(self, vertices) -> 'Graph':
        subgraph = []
        visited = dict.fromkeys(self.vertices(), False)
        def visit(v):
            stack = [v]
            while len(stack) != 0:
                v = stack[-1]
                stack.pop()
                if v in visited and not visited[v]:
                    visited[v] = True
                    subgraph.append(v)
                    for u in self.out_neighbors(v):
                        if not visited[u]:
                            stack.append(u)
        for v in vertices:
            visit(v)
        return self.subgraph(subgraph)

    def subgraph(self, vertices) -> 'Graph':
        subgraph_adjacency_list = {}
        for u in self.adjacency_list:
            if u in vertices:
                subgraph_adjacency_list[u] = list(
                    filter(lambda x: x in vertices, self.adjacency_list[u]))

        return Graph[T](subgraph_adjacency_list)

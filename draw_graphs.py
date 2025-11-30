import matplotlib.pyplot as plt
import numpy as np
import networkx as nx

def draw_graph_quantiles(G, weight_attr="count", title=""):
    # jobb på kopi og fjern self-loops
    G = G.copy()
    G.remove_edges_from([(u, v) for u, v in G.edges() if u == v])

    # hent vekter
    weights = np.array([G[u][v].get(weight_attr, 1) for u, v in G.edges()])
    if len(weights) == 0:
        print("Ingen kanter å tegne")
        return

    # kvantiler → legg kanter i 5 klasser
    qs = np.quantile(weights, [0, 0.2, 0.4, 0.6, 0.8, 1.0])
    widths = []
    for w in weights:
        if w <= qs[1]:
            widths.append(0.5)
        elif w <= qs[2]:
            widths.append(1.5)
        elif w <= qs[3]:
            widths.append(3.0)
        elif w <= qs[4]:
            widths.append(5.0)
        else:
            widths.append(7.0)   # topp 20% blir tykke

    pos = nx.spring_layout(G, seed=1, k=0.7)

    plt.figure(figsize=(6, 6))
    nx.draw(
        G,
        pos,
        with_labels=True,
        node_size=1100,
        node_color="#ddeeff",
        edge_color="#444444",
        width=widths,
        arrows=G.is_directed(),
        arrowstyle="-|>" if G.is_directed() else "-",
        arrowsize=18,
    )
    plt.title(title)
    plt.axis("off")
    plt.tight_layout()
    plt.show()

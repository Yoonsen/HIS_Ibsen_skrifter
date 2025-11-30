"""
ibsen_networks.py

Bygger talenettverk og co-occurrence-nettverk for Ibsens skuespill
fra en pars(et) JSON-struktur (ibsen_parsed.json), og eksporterer
dem til et PWA/visualiseringsvennlig JSON-format.
"""

from __future__ import annotations

import json
import re
from itertools import combinations
from typing import Any, Dict, List, Tuple

import networkx as nx


# -----------------------
# Navnerensing
# -----------------------

def normalize_name(name: str | None) -> str | None:
    """
    Normaliserer karakternavn som kommer fra cast-listen.

    Strategi:
    - Ta bare det som står før første komma (dropper rollebeskrivelse)
    - Slår sammen whitespace og linjeskift til enkeltmellomrom
    """
    if not name:
        return None
    # bare før første komma
    name = name.split(",")[0]
    # normaliser whitespace
    name = " ".join(name.split())
    return name or None


# -----------------------
# Talenettverk + transitions
# -----------------------

def build_speech_network_and_transitions(
    play: Dict[str, Any]
) -> Tuple[nx.DiGraph, List[Dict[str, Any]]]:
    """
    Bygg et rettet talenettverk for ett stykke + en liste med «transitions».

    Nodes: normaliserte karakternavn
    Edges u->v:
        - count: hvor ofte v snakker etter u
        - len_A_sum / len_B_sum: sum(talelengder) for u/v i disse overgangene

    Transitions: liste av dicts med:
        - play, act, scene, pos_in_scene
        - current_speaker, next_speaker
        - len_current, len_next
        - scene_speakers (normaliserte navn i scenen)
    """
    G = nx.DiGraph()
    transitions: List[Dict[str, Any]] = []

    for act in play.get("acts", []):
        act_n = act.get("act_n", "")
        for scene in act.get("scenes", []):
            scene_n = scene.get("scene_n", "")
            speeches = scene.get("speeches", [])
            speakers_in_scene_raw = scene.get("speakers_in_scene", []) or []

            # normaliser scene-cast
            speakers_in_scene = sorted(
                {
                    normalize_name(s)
                    for s in speakers_in_scene_raw
                    if normalize_name(s)
                }
            )

            # bygg sekvens av (speaker, length)
            seq: List[Dict[str, Any]] = []
            for sp in speeches:
                raw_speaker = sp.get("speaker")
                speaker = normalize_name(raw_speaker)
                if not speaker:
                    continue

                text = sp.get("text", "") or ""
                length = sp.get("length")
                if length is None:
                    # fallback: enkel ordtelling
                    length = len(text.split())

                seq.append({"speaker": speaker, "length": length})

            # trenger minst to replikker for å få en overgang
            if len(seq) < 2:
                continue

            for i in range(len(seq) - 1):
                a = seq[i]["speaker"]
                b = seq[i + 1]["speaker"]
                len_a = seq[i]["length"]
                len_b = seq[i + 1]["length"]

                if not a or not b:
                    continue

                if not G.has_node(a):
                    G.add_node(a)
                if not G.has_node(b):
                    G.add_node(b)

                if G.has_edge(a, b):
                    G[a][b]["count"] += 1
                    G[a][b]["len_A_sum"] += len_a
                    G[a][b]["len_B_sum"] += len_b
                else:
                    G.add_edge(
                        a,
                        b,
                        count=1,
                        len_A_sum=len_a,
                        len_B_sum=len_b,
                    )

                transitions.append(
                    {
                        "play": play.get("title", ""),
                        "act": act_n,
                        "scene": scene_n,
                        "pos_in_scene": i,
                        "current_speaker": a,
                        "next_speaker": b,
                        "len_current": len_a,
                        "len_next": len_b,
                        "scene_speakers": speakers_in_scene,
                    }
                )

    # fjern selv-loops
    loops = [(u, v) for u, v in G.edges() if u == v]
    if loops:
        G.remove_edges_from(loops)

    return G, transitions


# -----------------------
# Co-occurrence-nettverk
# -----------------------

def build_cooccurrence_network(play: Dict[str, Any]) -> nx.Graph:
    """
    Bygg et co-occurrence-nettverk for ett stykke.

    Node: normalisert karakternavn
    Edge u--v:
        - weight: antall scener der u og v begge er til stede
    """
    G = nx.Graph()

    for act in play.get("acts", []):
        for scene in act.get("scenes", []):
            speakers_raw = scene.get("speakers_in_scene", []) or []
            speakers = sorted(
                {
                    normalize_name(s)
                    for s in speakers_raw
                    if normalize_name(s)
                }
            )
            if len(speakers) < 2:
                continue

            # legg inn noder
            for s in speakers:
                if not G.has_node(s):
                    G.add_node(s)

            # legg inn par som co-occurrence
            for a, b in combinations(speakers, 2):
                if G.has_edge(a, b):
                    G[a][b]["weight"] += 1
                else:
                    G.add_edge(a, b, weight=1)

    return G


# -----------------------
# Eksport til PWA-/visualiserings-JSON
# -----------------------

def export_ibsen_networks(
    all_plays: List[Dict[str, Any]],
    outfile: str = "ibsen_networks.json",
) -> str:
    """
    Gitt hele listen `all_plays` (fra ibsen_parsed.json), bygg:

    - talenettverk per stykke
    - co-occurrence-nettverk per stykke

    og lagre alt i én JSON-fil med schema:

    {
      "plays": [
        {
          "id": "...",
          "title": "...",
          "speech_network": {
            "nodes": [{"id": "NORA"}, ...],
            "edges": [
              {
                "source": "NORA",
                "target": "HELMER",
                "count": 235,
                "avg_len_A": ...,
                "avg_len_B": ...
              },
              ...
            ]
          },
          "co_network": {
            "nodes": [...],
            "edges": [
              {"source": "NORA", "target": "HELMER", "weight": 5},
              ...
            ]
          }
        },
        ...
      ]
    }
    """
    export: Dict[str, Any] = {"plays": []}

    for play in all_plays:
        title = play.get("title", "")
        play_id = title  # evt. juster hvis du vil splitte ut årstall

        # talenettverk
        G_speech, transitions = build_speech_network_and_transitions(play)

        speech_nodes = [{"id": n} for n in G_speech.nodes()]
        speech_edges: List[Dict[str, Any]] = []
        for u, v, d in G_speech.edges(data=True):
            c = d.get("count", 1)
            len_A_sum = d.get("len_A_sum", 0)
            len_B_sum = d.get("len_B_sum", 0)
            speech_edges.append(
                {
                    "source": u,
                    "target": v,
                    "count": c,
                    "avg_len_A": len_A_sum / c if c else 0.0,
                    "avg_len_B": len_B_sum / c if c else 0.0,
                }
            )

        # co-occurrence-nettverk
        G_co = build_cooccurrence_network(play)
        co_nodes = [{"id": n} for n in G_co.nodes()]
        co_edges: List[Dict[str, Any]] = []
        for u, v, d in G_co.edges(data=True):
            co_edges.append(
                {
                    "source": u,
                    "target": v,
                    "weight": d.get("weight", 1),
                }
            )

        export["plays"].append(
            {
                "id": play_id,
                "title": play_id,
                "speech_network": {
                    "nodes": speech_nodes,
                    "edges": speech_edges,
                },
                "co_network": {
                    "nodes": co_nodes,
                    "edges": co_edges,
                },
            }
        )

    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(export, f, ensure_ascii=False, indent=2)

    return outfile






# -----------------------
# CLI / enkel kjøring
# -----------------------

def load_parsed(path: str = "ibsen_parsed.json") -> List[Dict[str, Any]]:
    """Hjelpefunksjon: last inn den parse-de JSON-en du allerede har laget."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    # Enkel «kjør alt»-modus:
    plays = load_parsed("ibsen_parsed.json")
    out = export_ibsen_networks(plays, "ibsen_networks.json")
    print("Skrev:", out)

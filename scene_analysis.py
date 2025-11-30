import pandas as pd
from math import comb  # Python 3.8+

import pandas as pd

def scene_drama_table(play, transitions):
    # samme som scene_comedy_table, bare evt. rename på sikt
    rows = []
    title = play.get("title", "")

    for act in play["acts"]:
        act_n = act.get("act_n", "")
        for scene in act["scenes"]:
            scene_n = scene.get("scene_n", "")
            cast = scene.get("speakers_in_scene", []) or []
            cast = sorted({s for s in cast if s})
            k = len(cast)
            if k < 2:
                continue

            from math import comb
            possible_pairs = comb(k, 2)

            scene_trans = [
                t for t in transitions
                if t["act"] == act_n and t["scene"] == scene_n
            ]
            pairs = {
                tuple(sorted((t["current_speaker"], t["next_speaker"])))
                for t in scene_trans
                if t["current_speaker"] != t["next_speaker"]
            }
            actual_pairs = len(pairs)
            drama_factor = actual_pairs / possible_pairs if possible_pairs else 0.0

            rows.append({
                "play": title,
                "act": act_n,
                "scene": scene_n,
                "cast_size": k,
                "possible_pairs": possible_pairs,
                "actual_pairs": actual_pairs,
                "drama_factor": drama_factor,      # <- nytt navn
            })

    return pd.DataFrame(rows)




def scene_comedy_table(play, transitions):
    rows = []
    title = play.get("title", "")

    for act in play["acts"]:
        act_n = act.get("act_n", "")
        for scene in act["scenes"]:
            scene_n = scene.get("scene_n", "")
            cast = scene.get("speakers_in_scene", []) or []
            cast = sorted({s for s in cast if s})
            k = len(cast)
            if k < 2:
                continue

            # mulige par i scenen
            possible_pairs = comb(k, 2)

            # faktiske par fra transitions for denne scenen
            scene_trans = [
                t for t in transitions
                if t["act"] == act_n and t["scene"] == scene_n
            ]
            # vi vil ha unike urettede par {A,B}
            pairs = {
                tuple(sorted((t["current_speaker"], t["next_speaker"])))
                for t in scene_trans
                if t["current_speaker"] != t["next_speaker"]
            }
            actual_pairs = len(pairs)
            density = actual_pairs / possible_pairs if possible_pairs else 0.0

            rows.append({
                "play": title,
                "act": act_n,
                "scene": scene_n,
                "cast_size": k,
                "possible_pairs": possible_pairs,
                "actual_pairs": actual_pairs,
                "comedy_factor": density,
            })

    return pd.DataFrame(rows)

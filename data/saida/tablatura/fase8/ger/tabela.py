import json, subprocess, sys
from pathlib import Path
B = Path("/app/data/saida/fase8/ger")
VIDS = ["greensleeves_guia_de_estudio_partitura_tab_pdf",
        "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar",
        "south_american_music_easy_guitar_tutorial_with_sheet_and_tab",
        "tab_from_this_place_pat_metheny_fingerstyle_guitar_cover",
        "end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics",
        "tabroom_335_larry_carlton_fingerstyle_guitar"]
out = {}
for d in ["base", "base_s2", "base_s3", "ger", "ger_s2", "ger_s3"]:
    for v in VIDS:
        j = B / "tab" / f"{d}_{v}.json"
        j.parent.mkdir(exist_ok=True)
        subprocess.run([sys.executable, "-m", "tab.avaliar_video", "--ouro",
                        f"/app/data/gold/ouro_video/{v}.json", "--pred", str(B / d / f"{v}.json"),
                        "--json", str(j)], check=True, cwd="/app", capture_output=True)
        n = json.loads(j.read_text())["notas"]
        out[f"{d}|{v}"] = {k: n[k] for k in n if not isinstance(n[k], (list, dict))}
print(json.dumps(out))

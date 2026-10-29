"""Fusiona fuentes/lote2.tsv en tiendas.json sin duplicar tiendas."""
import csv, json, re, unicodedata
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent
CERCA = {"Maipú", "Cerrillos", "Pudahuel", "Estación Central", "Lo Prado", "Padre Hurtado"}
CENTRO = {"Santiago Centro", "Providencia"}
BUENAS = {"Sitio web activo", "Directorio TorneosTCG", "Expositor TCG CON 2026", "Expositor Trading Fest 2026",
          "Lista oficial Bandai", "Lista oficial Digimon", "Lista oficial Gundam", "Comparador Card Pulse", "Localizador Wizards", "Instagram activo"}


def slug(s):
    s = unicodedata.normalize("NFD", s.lower()).encode("ascii", "ignore").decode()
    s = re.sub(r"\((web)\)", "", s)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def clave(nombre):
    return re.sub(r"-(tcg|store|chile|games|tienda)$", "", slug(nombre))


def prioridad(t):
    if t["region"] == "RM" and (t["comuna"] in CERCA or (t["comuna"] in CENTRO and t["eventos"])):
        return "A"
    if t["validacion"] == "Por confirmar" or t["tipo"] in ("Online TCG", "Cómics / manga", "Anime / coleccionables", "Juguetería", "Hobbies"):
        return "C" if t["region"] != "RM" or t["validacion"] == "Por confirmar" else "B"
    return "B"


def canal(t):
    if t["region"] == "RM" and t["tipo"] not in ("Online TCG",) and t["direccion"]:
        return "Visita en persona" if t["comuna"] in CERCA else "Visita + email"
    return "Email" if t["web"] else "Instagram / WhatsApp"


def main():
    tiendas = json.loads((AQUI / "tiendas.json").read_text(encoding="utf-8"))
    por_clave = {clave(t["nombre"]): t for t in tiendas}
    for t in tiendas:
        t.setdefault("tipo", "TCG")
        t.setdefault("email", "")
    nuevas = 0
    with (AQUI / "fuentes" / "lote2.tsv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            k = clave(r["nombre"])
            existente = por_clave.get(k)
            if existente:
                # Completa campos vacíos de la tienda ya listada.
                for campo in ("direccion", "web"):
                    if not existente.get(campo) and r[campo]:
                        existente[campo] = r[campo]
                if existente["validacion"] == "Por confirmar" and r["validacion"] in BUENAS:
                    existente["validacion"], existente["fuente"] = r["validacion"], r["fuente"]
                continue
            t = {"id": k, "nombre": r["nombre"].replace(" (web)", ""), "comuna": r["comuna"], "region": r["region"],
                 "direccion": r["direccion"], "web": r["web"], "juegos": r["juegos"], "eventos": r["eventos"] == "1",
                 "validacion": r["validacion"], "fuente": r["fuente"], "tipo": r["tipo"], "email": ""}
            t["prioridad"] = prioridad(t)
            t["canal"] = canal(t)
            tiendas.append(t)
            por_clave[k] = t
            nuevas += 1
    (AQUI / "tiendas.json").write_text(json.dumps(tiendas, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{nuevas} nuevas, total {len(tiendas)}")


if __name__ == "__main__":
    main()

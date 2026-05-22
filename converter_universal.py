# -*- coding: utf-8 -*-
"""
CONVERTISSEUR ECCODES → FORMAT GRIB-JSON (type grib2json / leaflet-velocity)
Entrée : f.grb2
Sortie : wind.json
"""

from eccodes import (
    codes_grib_new_from_file,
    codes_get,
    codes_get_array,
    codes_is_defined,
    codes_release
)
import json
import numpy as np
from pathlib import Path
from datetime import datetime


INPUT_FILE = "f.grb2"
OUTPUT_FILE = "wind.json"


def to_int(x):
    try:
        return int(x)
    except:
        return 0

def safe_get(gid, key, default=None):
    try:
        return codes_get(gid, key)
    except Exception:
        return default



def main():

    if not Path(INPUT_FILE).exists():
        print("ERREUR : f.grb2 introuvable")
        return

    result = []

    with open(INPUT_FILE, "rb") as f:

        while True:
            gid = codes_grib_new_from_file(f)
            if gid is None:
                break

            shortName = safe_get(gid, "shortName", None)

            # print("Position fichier :", f.tell())

            # Si shortName est introuvable → on ignore ce message
            if not shortName:
                codes_release(gid)
                continue

            # Filtre des variables utiles
            if shortName not in (
                    "10u", "10v", "gust", "fg10", "prmsl",
                    "swh", "mwd", "mwp",
                    "shww", "mdww", "mpww"
            ):
                codes_release(gid)
                continue

            # --- Temps ---
            dataDate = to_int(codes_get(gid, "dataDate"))
            dataTime = to_int(codes_get(gid, "dataTime"))
            step     = to_int(codes_get(gid, "step"))

            ref_dt = datetime.strptime(f"{dataDate:08d}{dataTime:04d}", "%Y%m%d%H%M")
            refTime = ref_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

            # --- Métadonnées GRIB ---
            paramCat = to_int(safe_get(gid, "parameterCategory", -1))
            paramNum = to_int(safe_get(gid, "parameterNumber", -1))
            level    = to_int(codes_get(gid, "level"))
            typeOfLevel = codes_get(gid, "typeOfLevel")

            Ni = to_int(codes_get(gid, "Ni"))
            Nj = to_int(codes_get(gid, "Nj"))

            lo1 = float(codes_get(gid, "longitudeOfFirstGridPointInDegrees"))
            la1 = float(codes_get(gid, "latitudeOfFirstGridPointInDegrees"))
            lo2 = float(codes_get(gid, "longitudeOfLastGridPointInDegrees"))
            la2 = float(codes_get(gid, "latitudeOfLastGridPointInDegrees"))

            dx = (lo2 - lo1) / (Ni - 1) if Ni > 1 else 0.0
            dy = (la2 - la1) / (Nj - 1) if Nj > 1 else 0.0

            # unités
            if codes_is_defined(gid, "units"):
                unit = codes_get(gid, "units")
            else:
                unit = "unknown"

            # nom lisible
            if codes_is_defined(gid, "name"):
                paramName = codes_get(gid, "name")
            else:
                paramName = shortName

            # --- Données ---
            values = codes_get_array(gid, "values")
            arr2d = np.array(values).reshape(Nj, Ni)
            arr2d = np.round(arr2d, 1)

            header = {
                "shortName": shortName,
                "parameterUnit": unit,
                "parameterNumber": paramNum,
                "parameterCategory": paramCat,
                "parameterName": paramName,
                "typeOfLevel": typeOfLevel,
                "level": level,
                "nx": Ni,
                "ny": Nj,
                "forecastTime": step,
                "refTime": refTime,
                "lo1": lo1,
                "la1": la1,
                "lo2": lo2,
                "la2": la2,
                "dx": dx,
                "dy": dy
            }

            entry = {
                "header": header,
                "data": arr2d.flatten().tolist()
            }

            result.append(entry)

            codes_release(gid)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        json.dump(result, out, separators=(",", ":"), ensure_ascii=False)

    print(f"✔ Conversion terminée → {OUTPUT_FILE}")
    print(f"✔ Champs écrits : {len(result)}")


if __name__ == "__main__":
    main()

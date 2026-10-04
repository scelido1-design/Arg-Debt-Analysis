import argparse
from io import StringIO
from pathlib import Path

import pandas as pd
from db import get_conn

DATA = Path(__file__).resolve().parent.parent / "data"
LARGO = 171
CHUNK = 200_000
WIDTHS = [5, 6, 2, 11, 3, 2] + [12] * 11 + [1] * 6 + [4]
NAMES = ["cod_entidad", "periodo", "tipo_id", "cuit", "actividad", "situacion",
         "prestamos", "sin_uso", "garantias_otorgadas", "otros_conceptos",
         "gar_pref_a", "gar_pref_b", "sin_gar_pref", "contragar_a", "contragar_b",
         "sin_contragar", "previsiones", "deuda_cubierta", "proc_jud_rev",
         "refinanc", "recateg_oblig", "sit_juridica", "irrecuperable", "dias_atraso"]
MONTOS = NAMES[6:17]
ENTEROS = ["periodo", "tipo_id", "cuit", "actividad", "situacion", "deuda_cubierta",
           "proc_jud_rev", "refinanc", "recateg_oblig", "sit_juridica",
           "irrecuperable", "dias_atraso"]
COLS = ", ".join(NAMES)


def largo_linea(path):
    with open(path, encoding="latin-1") as f:
        return len(f.readline().rstrip("\r\n"))


def periodo_primera_linea(path):
    with open(path, encoding="latin-1") as f:
        return int(f.readline()[5:11])


def parse_monto(s):
    s = s.str.strip().str.replace(",", ".", regex=False)
    n = pd.to_numeric(s, errors="coerce")
    con_separador = s.str.contains(".", regex=False, na=False)
    return n.where(con_separador, n / 10).round(1)   # sin separador: 1 decimal implícito


def limpiar(df):
    df["cod_entidad"] = df["cod_entidad"].str.strip()
    for c in ENTEROS:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    for c in MONTOS:
        df[c] = parse_monto(df[c])
    return df[NAMES]


def cargar(path, muestra=None):
    periodo = periodo_primera_linea(path)
    total = 0
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM raw.bcra_deudores WHERE periodo = %s", (periodo,))
        with cur.copy(f"COPY raw.bcra_deudores ({COLS}) FROM STDIN WITH (FORMAT csv)") as cp:
            lector = pd.read_fwf(path, widths=WIDTHS, names=NAMES, dtype=str,
                                 encoding="latin-1", chunksize=CHUNK, nrows=muestra)
            for i, chunk in enumerate(lector, 1):
                buf = StringIO()
                limpiar(chunk).to_csv(buf, header=False, index=False)
                cp.write(buf.getvalue())
                total += len(chunk)
                if i % 10 == 0:
                    print(f"  {total:,} filas...", flush=True)
        cur.execute("INSERT INTO raw.carga_log (archivo, periodos, filas) VALUES (%s, %s, %s)",
                    (path.name, [periodo], total))
    print(f"{path.name}: {total:,} filas cargadas, período {periodo}")


def listar():
    return sorted((p for p in DATA.rglob("*") if p.is_file() and p.suffix.lower() != ".7z"),
                  key=lambda p: str(p).lower())


def resolver(nombre):
    p = Path(nombre)
    if p.is_file():
        return p
    for q in DATA.rglob("*"):
        if q.is_file() and q.name.lower() == p.name.lower():
            return q
    return None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("archivos", nargs="*")
    ap.add_argument("--muestra", type=int, help="cargar solo las primeras N filas (prueba)")
    args = ap.parse_args()
    print(f"Carpeta de datos: {DATA}")
    if not args.archivos:
        for p in listar():
            print(f"  {p.relative_to(DATA)}: {p.stat().st_size:,} bytes, "
                  f"primera línea de {largo_linea(p)} caracteres")
        raise SystemExit
    for nombre in args.archivos:
        p = resolver(nombre)
        if p is None:
            print(f"{nombre}: no se encontró bajo {DATA}.")
            continue
        if largo_linea(p) != LARGO:
            print(f"{p.name}: la línea mide {largo_linea(p)}, no {LARGO}. NO se carga.")
            continue
        cargar(p, args.muestra)
import pandas as pd
from db import get_conn

def analizar_estadisticas_deuda():
    # TABLESAMPLE SYSTEM(1) extrae aproximadamente el 1% de los bloques físicos de la tabla.
    # En 40 millones de filas, esto traerá unas 400.000 filas aleatorias muy rápido.
    # Filtramos prestamos > 0 para no sesgar el análisis con cuentas inactivas o sin saldo.
    query = """
        SELECT prestamos 
        FROM raw.bcra_deudores 
        TABLESAMPLE SYSTEM(1)
        WHERE prestamos > 0 AND LEFT(cuit::text, 2) IN ('20', '23', '24', '27') AND raw.bcra_deudores.situacion IN ('2','3','4','5');
    """
    
    print("Extrayendo muestra aleatoria de la base de datos...")
    
    with get_conn() as conn:
        df = pd.read_sql_query(query, conn)
        
    total_filas = len(df)
    if total_filas == 0:
        print("No se obtuvieron datos. Verifica que la tabla tenga registros.")
        return

    print(f"Muestra analizada: {total_filas:,} registros.")

    # 1. Media (Promedio)
    media = df['prestamos'].mean()
    
    # 2. Mediana
    mediana = df['prestamos'].median()
    
    # 3. Moda
    moda = df['prestamos'].mode().iloc[0]

    print("\n--- Estadísticas de Capital Adeudado (morosos) ---")
    print(f"Media (Promedio) : $ {media * 1000:,.2f}")
    print(f"Mediana          : $ {mediana * 1000:,.2f}")
    print(f"Moda             : $ {moda * 1000:,.2f}")

if __name__ == "__main__":
    analizar_estadisticas_deuda()
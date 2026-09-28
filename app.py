from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Control de Finanzas", page_icon="💰", layout="wide"
)

# Archivo local para simular la base de datos (puedes cambiarlo a la nube después)
DATA_FILE = "transacciones.csv"


def cargar_datos():
  try:
    df = pd.read_csv(DATA_FILE)
    df["Fecha"] = pd.to_datetime(df["Fecha"])
    return df
  except FileNotFoundError:
    # Si no existe, creamos un DataFrame vacío con las columnas necesarias
    return pd.DataFrame(columns=["Fecha", "Tipo", "Categoría", "Monto", "Nota"])


def guardar_datos(df):
  df.to_csv(DATA_FILE, index=False)


# Cargar datos actuales
df_transacciones = cargar_datos()

# Título de la App
st.title("💸 Control de Gastos e Ingresos")
st.markdown("Gestiona tus finanzas personales desde la PC o el celular.")

# --- MENÚ LATERAL: AGREGAR TRANSACCIÓN ---
st.sidebar.header("Nueva Transacción")

tipo = st.sidebar.selectbox("Tipo", ["Gasto", "Ingreso"])

# Categorías sugeridas
if tipo == "Gasto":
  categorias = [
      "Comida / Supermercado",
      "Transporte",
      "Servicios",
      "Entretenimiento",
      "Varios",
  ]
else:
  categorias = ["Sueldo", "Freelance / Extra", "Regalos", "Otros"]

categoria = st.sidebar.selectbox("Categoría", categorias)
monto = st.sidebar.number_input("Monto ($)", min_value=0.0, step=100.0)
fecha = st.sidebar.date_input("Fecha", datetime.today())
nota = st.sidebar.text_input("Nota / Descripción (opcional)")

if st.sidebar.button("Registrar Movimiento"):
  if monto > 0:
    nueva_fila = pd.DataFrame(
        {
            "Fecha": [pd.to_datetime(fecha)],
            "Tipo": [tipo],
            "Categoría": [categoria],
            "Monto": [monto],
            "Nota": [nota if nota else "-"],
        }
    )
    df_transacciones = pd.concat(
        [df_transacciones, nueva_fila], ignore_index=True
    )
    guardar_datos(df_transacciones)
    st.sidebar.success("¡Movimiento guardado con éxito!")
    st.rerun()
  else:
    st.sidebar.error("El monto debe ser mayor a 0.")

# --- PANEL PRINCIPAL (DASHBOARD) ---
if not df_transacciones.empty:
  # Cálculos generales
  total_ingresos = df_transacciones[df_transacciones["Tipo"] == "Ingreso"][
      "Monto"
  ].sum()
  total_gastos = df_transacciones[df_transacciones["Tipo"] == "Gasto"][
      "Monto"
  ].sum()
  balance = total_ingresos - total_gastos

  # Tarjetas de resumen
  col1, col2, col3 = st.columns(3)
  col1.metric("💰 Total Ingresos", f"${total_ingresos:,.2f}")
  col2.metric("💸 Total Gastos", f"${total_gastos:,.2f}")
  col3.metric(
      "⚖️ Balance",
      f"${balance:,.2f}",
      delta=f"${balance:,.2f}",
      delta_color="normal" if balance >= 0 else "inverse",
  )

  st.divider()

  # Gráficos y Tablas
  col_g1, col_g2 = st.columns(2)

  with col_g1:
    st.subheader("Gastos por Categoría")
    df_gastos = df_transacciones[df_transacciones["Tipo"] == "Gasto"]
    if not df_gastos.empty:
      fig_gastos = px.pie(
          df_gastos,
          names="Categoría",
          values="Monto",
          hole=0.4,
          color_discrete_sequence=px.colors.sequential.Sunset,
      )
      st.plotly_chart(fig_gastos, use_container_width=True)
    else:
      st.info("No hay gastos registrados todavía.")

  with col_g2:
    st.subheader("Evolución de Movimientos")
    # Ordenar por fecha para mostrar bien el historial gráfico
    fig_line = px.bar(
        df_transacciones,
        x="Fecha",
        y="Monto",
        color="Tipo",
        barmode="group",
        color_discrete_map={"Ingreso": "#00CC96", "EF": "#EF553B"},
    )
    st.plotly_chart(fig_line, use_container_width=True)

  # Tabla de historial con opción de borrar
  st.subheader("Historial de Movimientos")

  # Mostrar ordenado del más reciente al más antiguo
  df_mostrar = df_transacciones.sort_values(by="Fecha", ascending=False).copy()
  df_mostrar["Fecha"] = df_mostrar["Fecha"].dt.strftime("%Y-%m-%d")

  # Mostramos la tabla interactiva
  st.dataframe(df_mostrar, use_container_width=True)

  # Botón para limpiar todo o borrar registros si fuera necesario
  if st.button("Borrar último registro agregado"):
    df_transacciones = df_transacciones.iloc[:-1]
    guardar_datos(df_transacciones)
    st.rerun()

else:
  st.info(
      "Aún no hay transacciones cargadas. Usa el menú lateral izquierdo para"
      " comenzar a registrar tus ingresos y gastos."
  )
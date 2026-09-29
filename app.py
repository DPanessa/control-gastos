from datetime import datetime
import io
import json
import os
import time
from google import genai
from google.genai import types
import pandas as pd
import plotly.express as px
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Control de Finanzas Multi-Usuario", page_icon="💰", layout="wide"
)

# Archivos de datos
USERS_FILE = "usuarios.csv"
DATA_FILE = "transacciones.csv"
CATEGORIES_FILE = "categorias.csv"
SESSION_FILE = "sesion_activa.txt"
LOGIN_LOG_FILE = "login_log.csv"

# Categorías por defecto base
DEFAULT_GASTOS = [
    "Comida / Supermercado",
    "Transporte",
    "Servicios",
    "Entretenimiento",
    "Varios",
]
DEFAULT_INGRESOS = ["Sueldo", "Freelance / Extra", "Regalos", "Otros"]


# --- CONFIGURACIÓN DE GEMINI (OCR / INTELIGENCIA ARTIFICIAL) ---
def obtener_cliente_gemini():
  api_key = None
  try:
    if "GEMINI_API_KEY" in st.secrets:
      api_key = st.secrets["GEMINI_API_KEY"]
  except Exception:
    pass

  if not api_key:
    api_key = os.environ.get("GEMINI_API_KEY", "")

  if api_key:
    return genai.Client(api_key=api_key)
  return None


# --- OBTENER IP DEL CLIENTE ---
def obtener_ip_cliente():
  try:
    headers = st.context.headers
    ip = (
        headers.get("X-Forwarded-For", "").split(",")[0]
        or headers.get("X-Real-Ip", "")
        or "127.0.0.1"
    )
    return ip.strip()
  except Exception:
    return "127.0.0.1"


# --- FUNCIONES DE REGISTRO DE LOGIN / LOGOUT ---
def cargar_login_log():
  if not os.path.exists(LOGIN_LOG_FILE):
    df_init = pd.DataFrame(
        columns=["Usuario", "IP", "Conexion", "Desconexion"]
    )
    df_init.to_csv(LOGIN_LOG_FILE, index=False)
    return df_init
  try:
    return pd.read_csv(LOGIN_LOG_FILE)
  except Exception:
    return pd.DataFrame(columns=["Usuario", "IP", "Conexion", "Desconexion"])


def registrar_login_log(usuario, ip, accion):
  df_log = cargar_login_log()
  ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  if accion == "Login":
    nuevo = pd.DataFrame(
        {
            "Usuario": [usuario],
            "IP": [ip],
            "Conexion": [ahora],
            "Desconexion": [""],
        }
    )
    df_log = pd.concat([df_log, nuevo], ignore_index=True)
  else:
    idx = df_log[
        (df_log["Usuario"] == usuario)
        & (df_log["Desconexion"].isna() | (df_log["Desconexion"] == ""))
    ].index
    if not idx.empty:
      df_log.loc[idx[-1], "Desconexion"] = ahora
  df_log.to_csv(LOGIN_LOG_FILE, index=False)


# --- FUNCIONES DE USUARIOS Y SESIÓN LOCAL ---
def cargar_usuarios():
  if not os.path.exists(USERS_FILE):
    df_init = pd.DataFrame(columns=["Usuario", "Password"])
    df_init.to_csv(USERS_FILE, index=False)
    return df_init
  try:
    return pd.read_csv(USERS_FILE)
  except Exception:
    return pd.DataFrame(columns=["Usuario", "Password"])


def guardar_usuario(usuario, password):
  df_users = cargar_usuarios()
  if not df_users.empty and usuario in df_users["Usuario"].values:
    return False
  nuevo_u = pd.DataFrame({"Usuario": [usuario], "Password": [password]})
  df_users = pd.concat([df_users, nuevo_u], ignore_index=True)
  df_users.to_csv(USERS_FILE, index=False)
  return True


def validar_usuario(usuario, password):
  df_users = cargar_usuarios()
  if df_users.empty:
    return False
  match = df_users[
      (df_users["Usuario"] == usuario) & (df_users["Password"] == password)
  ]
  return not match.empty


def leer_sesion_local():
  if os.path.exists(SESSION_FILE):
    with open(SESSION_FILE, "r") as f:
      contenido = f.read().strip()
      # Formato esperado: USUARIO|IP
      if "|" in contenido:
        return contenido.split("|")[0]
      return contenido
  return None


def guardar_sesion_local(usuario, ip):
  with open(SESSION_FILE, "w") as f:
    f.write(f"{usuario}|{ip}")


def borrar_sesion_local(usuario):
  if usuario:
    registrar_login_log(usuario, obtener_ip_cliente(), "Logout")
  if os.path.exists(SESSION_FILE):
    os.remove(SESSION_FILE)


# --- SISTEMA DE AUTENTICACIÓN PERSISTENTE ---
if "usuario_actual" not in st.session_state:
  st.session_state.usuario_actual = leer_sesion_local()

if not st.session_state.usuario_actual:
  st.title("🔐 Control de Gastos Personales")
  tab1, tab2 = st.tabs(["Iniciar Sesión", "Registrarse"])

  with tab1:
    st.subheader("Accede a tu cuenta")
    user_in = st.text_input("Usuario", key="login_user")
    pass_in = st.text_input("Contraseña", type="password", key="login_pass")
    if st.button("Entrar"):
      if validar_usuario(user_in, pass_in):
        ip_actual = obtener_ip_cliente()
        st.session_state.usuario_actual = user_in
        guardar_sesion_local(user_in, ip_actual)
        registrar_login_log(user_in, ip_actual, "Login")
        st.rerun()
      else:
        st.error("Usuario o contraseña incorrectos.")

  with tab2:
    st.subheader("Crea una cuenta nueva")
    user_reg = st.text_input("Nuevo Usuario", key="reg_user")
    pass_reg = st.text_input("Nueva Contraseña", type="password", key="reg_pass")
    if st.button("Registrarse"):
      if user_reg and pass_reg:
        if guardar_usuario(user_reg, pass_reg):
          st.success(
              "¡Cuenta creada con éxito! (Si creaste 'admin', tendrás privilegios"
              " de superusuario). Ve a la pestaña 'Iniciar Sesión'."
          )
        else:
          st.error("El nombre de usuario ya está en uso.")
      else:
        st.warning("Por favor completa ambos campos.")

  st.stop()


# --- FUNCIONES DE CATEGORÍAS PERSONALIZADAS ---
def cargar_categorias_custom():
  if not os.path.exists(CATEGORIES_FILE):
    df_init = pd.DataFrame(columns=["Usuario", "Tipo", "Categoria"])
    df_init.to_csv(CATEGORIES_FILE, index=False)
    return df_init
  try:
    return pd.read_csv(CATEGORIES_FILE)
  except Exception:
    return pd.DataFrame(columns=["Usuario", "Tipo", "Categoria"])


def guardar_categoria_custom(usuario, tipo, categoria):
  df_cat = cargar_categorias_custom()
  existente = False
  if not df_cat.empty:
    existente = not df_cat[
        (df_cat["Usuario"] == usuario)
        & (df_cat["Tipo"] == tipo)
        & (df_cat["Categoria"].str.lower() == categoria.lower())
    ].empty

  if existente:
    return False

  nueva = pd.DataFrame(
      {"Usuario": [usuario], "Tipo": [tipo], "Categoria": [categoria]}
  )
  df_cat = pd.concat([df_cat, nueva], ignore_index=True)
  df_cat.to_csv(CATEGORIES_FILE, index=False)
  return True


def obtener_categorias(usuario, tipo):
  base = DEFAULT_GASTOS if tipo == "Gasto" else DEFAULT_INGRESOS
  df_cat = cargar_categorias_custom()
  if not df_cat.empty:
    customs = df_cat[
        (df_cat["Usuario"] == usuario) & (df_cat["Tipo"] == tipo)
    ]["Categoria"].tolist()
    return sorted(list(set(base + customs)))
  return base


# --- FUNCIONES DE TRANSACCIONES ---
def cargar_datos():
  if not os.path.exists(DATA_FILE):
    df_init = pd.DataFrame(
        columns=["Usuario", "Fecha", "Tipo", "Cuenta", "Categoría", "Monto", "Nota"]
    )
    df_init.to_csv(DATA_FILE, index=False)
    return df_init
  try:
    df = pd.read_csv(DATA_FILE)
    df["Fecha"] = pd.to_datetime(df["Fecha"])
    if "Usuario" not in df.columns:
      df["Usuario"] = "admin"
    if "Cuenta" not in df.columns:
      df["Cuenta"] = "Bancario (Digital)"
    return df
  except Exception:
    return pd.DataFrame(
        columns=["Usuario", "Fecha", "Tipo", "Cuenta", "Categoría", "Monto", "Nota"]
    )


def guardar_datos(df):
  df.to_csv(DATA_FILE, index=False)


df_global = cargar_datos()

# Gestión de Superusuario
es_superusuario = st.session_state.usuario_actual.lower() == "admin"
ver_modo_global = False

if es_superusuario:
  st.sidebar.warning("🛡️ Modo Superusuario Activo")
  ver_modo_global = st.sidebar.checkbox(
      "Ver datos globales (todos los usuarios)", value=False
  )
  if ver_modo_global:
    df_transacciones = df_global.copy()
  else:
    df_transacciones = df_global[
        df_global["Usuario"] == st.session_state.usuario_actual
    ].copy()
else:
  df_transacciones = df_global[
      df_global["Usuario"] == st.session_state.usuario_actual
    ].copy()

# --- PANEL PRINCIPAL DE LA APP ---
st.title(f"💸 Finanzas de: {st.session_state.usuario_actual}")
st.markdown(
    "Gestiona tu dinero físico y bancario de forma privada y escanea tickets"
    " con IA."
)

if st.sidebar.button("Cerrar Sesión"):
  usuario_saliendo = st.session_state.usuario_actual
  st.session_state.usuario_actual = None
  borrar_sesion_local(usuario_saliendo)
  st.rerun()

st.sidebar.divider()

# --- MENÚ LATERAL: MODO MANUAL VS MODO OCR (IA) ---
modo_carga = st.sidebar.radio(
    "Método de registro", ["✍️ Manual", "📷 Escanear Ticket (IA)"]
)

client_gemini = obtener_cliente_gemini()

if modo_carga == "📷 Escanear Ticket (IA)":
  st.sidebar.subheader("Escanear Comprobante")
  if not client_gemini:
    st.sidebar.error(
        "Falta configurar la API Key de Gemini en los secrets o entorno."
    )
  else:
    foto_subida = st.sidebar.file_uploader(
        "Sube foto de ticket o factura", type=["jpg", "jpeg", "png"]
    )
    if foto_subida is not None:
      st.sidebar.image(
          foto_subida, caption="Ticket subido", use_container_width=True
      )
      if st.sidebar.button("Analizar con IA"):
        with st.spinner("Procesando imagen con IA..."):
          response = None
          for intento in range(1, 3):
            try:
              image_bytes = foto_subida.getvalue()
              response = client_gemini.models.generate_content(
                  model="gemini-3.8-flash",
                  contents=[
                      types.Part.from_bytes(
                          data=image_bytes, mime_type=foto_subida.type
                      ),
                      (
                          "Analiza este comprobante de gasto o pago y extrae en"
                          " formato estricto JSON lo siguiente: "
                          '{"monto": 0.0, "descripcion": "comercio o detalle",'
                          ' "tipo": "Gasto"} (si es ingreso pon Ingreso, sino'
                          " Gasto). Solo devuelve el JSON sin formato markdown"
                          " extra."
                      ),
                  ],
              )
              break
            except Exception:
              time.sleep(1)

          if response and response.text:
            try:
              backticks = chr(96) * 3
              texto_limpio = (
                  response.text.replace(backticks + "json", "")
                  .replace(backticks, "")
                  .strip()
              )
              datos_ticket = json.loads(texto_limpio)

              st.session_state.ocr_monto = float(datos_ticket.get("monto", 0.0))
              st.session_state.ocr_nota = str(
                  datos_ticket.get("descripcion", "Ticket escaneado")
              )
              st.sidebar.success("¡Comprobante leído con éxito!")
              st.rerun()
            except Exception:
              st.sidebar.warning(
                  "⚠️ No se pudo interpretar la respuesta exacta del ticket."
                  " Completa los datos manualmente."
              )
          else:
            st.sidebar.warning(
                "⚠️ Los servidores de IA están ocupados temporalmente. Completa"
                " los datos de forma manual."
            )

tipo = st.sidebar.selectbox("Tipo", ["Gasto", "Ingreso"])

tipo_dinero = st.sidebar.selectbox(
    "Tipo de Dinero", ["Físico (Efectivo)", "Bancario / Digital"]
)
if tipo_dinero == "Bancario / Digital":
  banco_seleccionado = st.sidebar.selectbox(
      "Banco o Billetera Virtual",
      [
          "Mercado Pago",
          "Lemon Cash",
          "BBVA",
          "Banco Galicia",
          "PayPal",
          "Otro (Personalizado)",
      ],
  )
  if banco_seleccionado == "Otro (Personalizado)":
    banco_seleccionado = st.sidebar.text_input(
        "Nombre del banco / billetera"
    ).strip()
    if not banco_seleccionado:
      banco_seleccionado = "Digital"
  cuenta = f"Digital: {banco_seleccionado}"
else:
  cuenta = "Físico (Efectivo)"

lista_categorias = obtener_categorias(
    st.session_state.usuario_actual, tipo
)
categoria = st.sidebar.selectbox("Categoría", lista_categorias)

with st.sidebar.expander("➕ Agregar nueva categoría"):
  nueva_cat_input = st.text_input(
      "Nombre de categoría", key="input_nueva_cat"
  )
  if st.button("Guardar Categoría"):
    if nueva_cat_input.strip():
      exito = guardar_categoria_custom(
          st.session_state.usuario_actual, tipo, nueva_cat_input.strip()
      )
      if exito:
        st.success(f"¡Categoría '{nueva_cat_input}' agregada!")
        st.rerun()
      else:
        st.warning("Esa categoría ya existe.")
    else:
      st.error("Escribe un nombre válido.")

default_monto = st.session_state.pop("ocr_monto", 0.0)
default_nota = st.session_state.pop("ocr_nota", "")

monto = st.sidebar.number_input(
    "Monto ($)", min_value=0.0, step=100.0, value=default_monto
)
fecha_input = st.sidebar.date_input("Fecha", datetime.today())
hora_input = st.sidebar.time_input("Hora", datetime.now().time())
fecha_hora_combinada = datetime.combine(fecha_input, hora_input)

nota = st.sidebar.text_input("Nota / Descripción", value=default_nota)

if st.sidebar.button("Registrar Movimiento"):
  if monto > 0:
    nueva_fila = pd.DataFrame(
        {
            "Usuario": [st.session_state.usuario_actual],
            "Fecha": [pd.to_datetime(fecha_hora_combinada)],
            "Tipo": [tipo],
            "Cuenta": [cuenta],
            "Categoría": [categoria],
            "Monto": [monto],
            "Nota": [nota if nota else "-"],
        }
    )
    df_global = pd.concat([df_global, nueva_fila], ignore_index=True)
    guardar_datos(df_global)
    st.sidebar.success("¡Movimiento guardado con éxito!")
    st.rerun()
  else:
    st.sidebar.error("El monto debe ser mayor a 0.")

# Botón de respaldo para descargar CSV en la barra lateral
st.sidebar.divider()
if not df_global.empty:
  csv_data = df_global.to_csv(index=False).encode("utf-8")
  st.sidebar.download_button(
      label="📥 Descargar Respaldo CSV",
      data=csv_data,
      file_name="transacciones_respaldo.csv",
      mime="text/csv",
  )

# --- DASHBOARD Y MÉTRICAS ---
if not df_transacciones.empty:
  st.subheader("📊 Estado de tus Cuentas y Billeteras")

  cuentas_unicas = df_transacciones["Cuenta"].unique()
  cols = st.columns(len(cuentas_unicas) + 1)

  patrimonio_total = 0
  for i, cta in enumerate(cuentas_unicas):
    df_c = df_transacciones[df_transacciones["Cuenta"] == cta]
    ing = df_c[df_c["Tipo"] == "Ingreso"]["Monto"].sum()
    gas = df_c[df_c["Tipo"] == "Gasto"]["Monto"].sum()
    balance_cta = ing - gas
    patrimonio_total += balance_cta

    cols[i].metric(label=f"🏦 {cta}", value=f"${balance_cta:,.2f}")

  cols[-1].metric(
      label="💰 Patrimonio Total",
      value=f"${patrimonio_total:,.2f}",
      delta=f"${patrimonio_total:,.2f}",
      delta_color="normal" if patrimonio_total >= 0 else "inverse",
  )

  st.divider()

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
    st.subheader("Análisis Financiero")

    tipo_grafico = st.radio(
        "Elige qué gráfico mostrar:",
        [
            "📊 Comparación Ingresos / Gastos",
            "💳 Distribución por Cuentas",
        ],
        key="selector_grafico_fin",
    )

    if tipo_grafico == "📊 Comparación Ingresos / Gastos":
      total_ingresos = df_transacciones[df_transacciones["Tipo"] == "Ingreso"][
          "Monto"
      ].sum()
      total_gastos = df_transacciones[df_transacciones["Tipo"] == "Gasto"][
          "Monto"
      ].sum()
      fig_ing_gas = px.bar(
          x=["Ingresos", "Gastos"],
          y=[total_ingresos, total_gastos],
          color=["Ingresos", "Gastos"],
          color_discrete_map={"Ingresos": "#2ecc71", "Gastos": "#e74c3c"},
          labels={"x": "Concepto", "y": "Monto ($)"},
      )
      st.plotly_chart(fig_ing_gas, use_container_width=True)
    else:
      saldos_cuentas = []
      for cta in cuentas_unicas:
        df_c = df_transacciones[df_transacciones["Cuenta"] == cta]
        saldos_cuentas.append(
            df_c[df_c["Tipo"] == "Ingreso"]["Monto"].sum()
            - df_c[df_c["Tipo"] == "Gasto"]["Monto"].sum()
        )
      fig_cuentas = px.bar(
          x=list(cuentas_unicas),
          y=saldos_cuentas,
          color=list(cuentas_unicas),
          labels={"x": "Cuenta / Billetera", "y": "Monto ($)"},
      )
      st.plotly_chart(fig_cuentas, use_container_width=True)

  st.subheader("Historial de tus Movimientos")
  df_mostrar = df_transacciones.sort_values(by="Fecha", ascending=False).copy()
  df_mostrar["Fecha"] = df_mostrar["Fecha"].dt.strftime("%Y-%m-%d %H:%M:%S")

  if es_superusuario and ver_modo_global:
    columnas_orden = [
        "Usuario",
        "Tipo",
        "Cuenta",
        "Categoría",
        "Monto",
        "Nota",
        "Fecha",
    ]
  else:
    columnas_orden = ["Tipo", "Cuenta", "Categoría", "Monto", "Nota", "Fecha"]

  columnas_disponibles = [c for c in columnas_orden if c in df_mostrar.columns]

  st.dataframe(
      df_mostrar[columnas_disponibles],
      use_container_width=True,
  )

  if st.button("Borrar mi último registro agregado"):
    idx_usuario = df_global[
        df_global["Usuario"] == st.session_state.usuario_actual
    ].index
    if not idx_usuario.empty:
      df_global = df_global.drop(idx_usuario[-1])
      guardar_datos(df_global)
      st.rerun()

else:
  st.info(
      "Aún no tienes transacciones cargadas. Usa el menú lateral para empezar a"
      " registrar tus ingresos y gastos."
  )

"""
E-Ishikawa Safety App — Project Mexico
Desarrollado con Streamlit + Google Sheets como base de datos compartida.
Autor: Marcel Carmona — UABC / Cruz Roja Tijuana
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="E-Ishikawa Safety App",
    page_icon="🦺",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS para optimizar en móvil y estilo corporativo
st.markdown("""
<style>
    .stButton > button {
        background-color: #E63946;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        height: 3em;
        width: 100%;
    }
    .stButton > button:hover { background-color: #C1121F; }
    .metric-card {
        background: #f8f9fa;
        border-left: 4px solid #E63946;
        padding: 1rem;
        border-radius: 6px;
        margin-bottom: 0.5rem;
    }
    @media (max-width: 768px) {
        .main .block-container { padding: 0.5rem 0.8rem; }
        h1 { font-size: 1.3rem !important; }
        h3 { font-size: 1rem !important; }
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

NOMBRE_SPREADSHEET = "E-Ishikawa Safety App — Project Mexico"

ROLES = [
    "Intern 2025",
    "Intern 2026",
    "Intern 2025 & 2026",
    "On-site Leader",
    "Remote Leader",
    "Otro"
]

SUBCAUSAS = {
    "Mano de obra": [
        "Entrenamiento insuficiente",
        "Falta de conocimiento del Plan de Acción de Emergencia",
        "Capacidades de primeros auxilios insuficientes",
        "Falta de liderazgo en emergencias",
        "Fatiga",
        "Comportamientos inseguros"
    ],
    "Maquinaria": [
        "Herramientas defectuosas",
        "Uso incorrecto de herramientas",
        "Equipo eléctrico inseguro",
        "Escaleras inseguras",
        "Equipo de emergencia insuficiente"
    ],
    "Métodos": [
        "Falta de un Plan de Acción de Emergencias",
        "Emergencias no clasificadas",
        "Activación de emergencias confusa",
        "Roles no definidos",
        "Acceso de ambulancias no planificado",
        "Dirección del sitio desconocida",
        "Falta de simulacros"
    ],
    "Materiales": [
        "Mal almacenamiento de materiales",
        "Objetos punzocortantes expuestos",
        "Materiales combustibles mal almacenados",
        "Botiquín de primeros auxilios inadecuado",
        "EPP insuficiente"
    ],
    "Medio Ambiente": [
        "Calor extremo",
        "Lluvia / superficies resbaladizas",
        "Viento",
        "Terreno irregular",
        "Acceso remoto",
        "Obstáculos en rutas de evacuación"
    ],
    "Medición": [
        "Accidentes no registrados",
        "Near misses (casi accidentes) ignorados",
        "Falta de indicadores de seguridad",
        "Falta de análisis de causa raíz",
        "Falta de simulacros evaluados"
    ]
}

ENCABEZADOS = [
    "Timestamp", "Rol", "M_Critica", "Subcausas",
    "Porque_1", "Porque_2", "Porque_3_Causa_Raiz",
    "Frecuencia", "Impacto", "Propuesta_de_Cambio"
]


# ─────────────────────────────────────────────
# CONEXIÓN Y GESTIÓN DE GOOGLE SHEETS
# ─────────────────────────────────────────────
@st.cache_resource
def conectar_google():
    """Autentica con la API de Google usando las credenciales de Streamlit Secrets."""
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        cliente = gspread.authorize(creds)
        return cliente
    except Exception as e:
        st.error(f"❌ Error de autenticación con Google: {e}")
        return None


def obtener_o_crear_hoja(cliente):
    """
    Abre el spreadsheet de la app. Si no existe, lo crea automáticamente
    y configura los encabezados. La primera vez se comparte con el correo
    del propietario definido en Secrets.
    """
    try:
        spreadsheet = cliente.open(NOMBRE_SPREADSHEET)
    except gspread.SpreadsheetNotFound:
        # Crear nuevo spreadsheet
        spreadsheet = cliente.create(NOMBRE_SPREADSHEET)
        # Compartir con el propietario para que pueda verlo en Google Drive
        if "owner_email" in st.secrets:
            spreadsheet.share(
                st.secrets["owner_email"],
                perm_type="user",
                role="owner"
            )

    # Obtener o crear la hoja "Respuestas"
    try:
        hoja = spreadsheet.worksheet("Respuestas")
    except gspread.WorksheetNotFound:
        hoja = spreadsheet.add_worksheet(title="Respuestas", rows=2000, cols=15)
        hoja.append_row(ENCABEZADOS)
        # Formato de encabezados en negrita
        hoja.format("A1:J1", {"textFormat": {"bold": True}})

    return hoja


def cargar_datos(hoja):
    """Carga todas las respuestas del sheet como un DataFrame de pandas."""
    try:
        registros = hoja.get_all_records()
        if registros:
            df = pd.DataFrame(registros)
            df["Frecuencia"] = pd.to_numeric(df["Frecuencia"], errors="coerce")
            df["Impacto"] = pd.to_numeric(df["Impacto"], errors="coerce")
            return df
        return pd.DataFrame(columns=ENCABEZADOS)
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return pd.DataFrame(columns=ENCABEZADOS)


def guardar_respuesta(hoja, datos: dict):
    """Agrega una nueva fila con la respuesta del encuestado."""
    fila = [
        datos["timestamp"],
        datos["rol"],
        datos["m_critica"],
        " | ".join(datos["subcausas"]),
        datos["porque_1"],
        datos["porque_2"],
        datos["porque_3"],
        datos["frecuencia"],
        datos["impacto"],
        datos["propuesta"]
    ]
    hoja.append_row(fila, value_input_option="USER_ENTERED")


# ─────────────────────────────────────────────
# PESTAÑA 1 — ENCUESTA OPERATIVA
# ─────────────────────────────────────────────
def mostrar_encuesta(hoja):
    st.title("🦺 E-Ishikawa Safety App")
    st.caption("Project Mexico — Encuesta de Seguridad en Obra")
    st.markdown("---")

    with st.form("encuesta_ishikawa", clear_on_submit=True):

        # 1. Rol
        st.markdown("### 1. Tu rol en el programa")
        rol = st.selectbox("Selecciona tu rol:", ROLES, label_visibility="collapsed")

        st.markdown("---")

        # 2. M Crítica
        st.markdown("### 2. ¿Cuál M presenta hoy el mayor riesgo?")
        st.caption("Selecciona la categoría de las 6M de Ishikawa con mayor área de oportunidad:")
        m_critica = st.radio(
            "M crítica:",
            options=list(SUBCAUSAS.keys()),
            label_visibility="collapsed"
        )

        st.markdown("---")

        # 3. Subcausas (desplegadas según M seleccionada)
        st.markdown(f"### 3. Subcausas de **{m_critica}**")
        st.caption("Selecciona todas las que apliquen hoy en la obra:")
        subcausas_seleccionadas = []
        for opcion in SUBCAUSAS[m_critica]:
            if st.checkbox(opcion, key=f"sub_{opcion}"):
                subcausas_seleccionadas.append(opcion)

        st.markdown("---")

        # 4. Los 3 Porqués
        st.markdown("### 4. Análisis — Los 3 Porqués")
        porque_1 = st.text_area(
            "**¿Por qué 1?** — Describe el factor de riesgo específico que identificaste:",
            max_chars=300, height=80, placeholder="Ej: Los voluntarios no saben cómo activar una emergencia..."
        )
        porque_2 = st.text_area(
            "**¿Por qué 2?** — ¿Por qué ocurre esta situación en el día a día de la obra?",
            max_chars=300, height=80, placeholder="Ej: Porque nunca se realizó una capacitación formal al inicio del programa..."
        )
        porque_3 = st.text_area(
            "**¿Por qué 3 (Causa raíz)?** — ¿Cuál es el factor profundo o sistémico que lo origina?",
            max_chars=300, height=80, placeholder="Ej: Porque el programa no cuenta con un protocolo de inducción de seguridad estandarizado..."
        )

        st.markdown("---")

        # 5. Evaluación del riesgo
        st.markdown("### 5. Evaluación del riesgo")
        col1, col2 = st.columns(2)
        with col1:
            frecuencia = st.slider(
                "**Frecuencia** — ¿Con qué frecuencia ocurre esto?",
                min_value=1, max_value=5, value=3,
                help="1 = Casi nunca  |  5 = Todos los días"
            )
            st.caption(f"{'🟢' if frecuencia <= 2 else '🟡' if frecuencia == 3 else '🔴'} {frecuencia}/5")
        with col2:
            impacto = st.slider(
                "**Impacto** — ¿Qué tanto afecta la seguridad?",
                min_value=1, max_value=5, value=3,
                help="1 = Poco impacto  |  5 = Impacto crítico"
            )
            st.caption(f"{'🟢' if impacto <= 2 else '🟡' if impacto == 3 else '🔴'} {impacto}/5")

        st.markdown("---")

        # 6. Propuesta de cambio
        st.markdown("### 6. Tu propuesta")
        propuesta = st.text_area(
            "Si pudieras hacer **un solo cambio mañana** para mejorar la seguridad, ¿cuál sería?",
            max_chars=400, height=100,
            placeholder="Ej: Realizar un simulacro de evacuación el primer día de cada semana..."
        )

        st.markdown(" ")
        enviado = st.form_submit_button("✅ Enviar respuesta", use_container_width=True)

        if enviado:
            # Validaciones
            errores = []
            if not subcausas_seleccionadas:
                errores.append("Selecciona al menos una subcausa.")
            if not porque_1.strip():
                errores.append("Completa el ¿Por qué 1?")
            if not porque_2.strip():
                errores.append("Completa el ¿Por qué 2?")
            if not porque_3.strip():
                errores.append("Completa el ¿Por qué 3 (causa raíz)?")
            if not propuesta.strip():
                errores.append("Escribe tu propuesta de cambio.")

            if errores:
                for err in errores:
                    st.warning(f"⚠️ {err}")
            else:
                datos = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "rol": rol,
                    "m_critica": m_critica,
                    "subcausas": subcausas_seleccionadas,
                    "porque_1": porque_1.strip(),
                    "porque_2": porque_2.strip(),
                    "porque_3": porque_3.strip(),
                    "frecuencia": frecuencia,
                    "impacto": impacto,
                    "propuesta": propuesta.strip()
                }
                try:
                    guardar_respuesta(hoja, datos)
                    st.success("🎉 ¡Respuesta registrada! Gracias por contribuir a la seguridad de Project Mexico.")
                    st.balloons()
                except Exception as e:
                    st.error(f"No se pudo guardar la respuesta: {e}")


# ─────────────────────────────────────────────
# PESTAÑA 2 — DASHBOARD INTERACTIVO
# ─────────────────────────────────────────────
def mostrar_dashboard(hoja):
    st.title("📊 Dashboard de Seguridad")
    st.caption("Project Mexico — Análisis Ishikawa en tiempo real")

    col_refresh, _ = st.columns([1, 4])
    with col_refresh:
        if st.button("🔄 Actualizar datos"):
            st.cache_data.clear()
            st.rerun()

    df = cargar_datos(hoja)

    if df.empty:
        st.info("📭 Aún no hay respuestas registradas. Comparte la app con tu equipo para comenzar.")
        return

    # ── Métricas clave ──────────────────────────────────────────────
    st.markdown("### 📌 Métricas Clave")
    m1, m2, m3, m4 = st.columns(4)

    with m1:
        st.metric("Total de respuestas", len(df))
    with m2:
        m_top = df["M_Critica"].mode()[0] if "M_Critica" in df.columns else "—"
        st.metric("M más reportada", m_top)
    with m3:
        frec_prom = round(df["Frecuencia"].mean(), 1) if "Frecuencia" in df.columns else 0
        st.metric("Frecuencia promedio", f"{frec_prom}/5")
    with m4:
        imp_prom = round(df["Impacto"].mean(), 1) if "Impacto" in df.columns else 0
        st.metric("Impacto promedio", f"{imp_prom}/5")

    st.markdown("---")

    col_izq, col_der = st.columns(2)

    # ── Diagrama de Pareto de las 6M ────────────────────────────────
    with col_izq:
        st.markdown("### 📊 Pareto de las 6M")
        if "M_Critica" in df.columns:
            conteo = df["M_Critica"].value_counts().reset_index()
            conteo.columns = ["M", "Reportes"]
            conteo = conteo.sort_values("Reportes", ascending=False).reset_index(drop=True)
            conteo["% Acumulado"] = (conteo["Reportes"].cumsum() / conteo["Reportes"].sum() * 100).round(1)

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=conteo["M"], y=conteo["Reportes"],
                name="Reportes",
                marker_color="#E63946",
                text=conteo["Reportes"],
                textposition="outside"
            ))
            fig.add_trace(go.Scatter(
                x=conteo["M"], y=conteo["% Acumulado"],
                name="% Acumulado", yaxis="y2",
                line=dict(color="#457B9D", width=2.5),
                marker=dict(size=9, symbol="circle")
            ))
            fig.add_hline(
                y=80, line_dash="dash", line_color="orange",
                annotation_text="80%", yref="y2",
                annotation_position="top right"
            )
            fig.update_layout(
                yaxis=dict(title="Número de reportes"),
                yaxis2=dict(title="% Acumulado", overlaying="y", side="right", range=[0, 115]),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
                height=370,
                margin=dict(l=10, r=10, t=40, b=10),
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig, use_container_width=True)

    # ── Matriz Frecuencia vs. Impacto ───────────────────────────────
    with col_der:
        st.markdown("### 🎯 Frecuencia vs. Impacto")
        if all(c in df.columns for c in ["Frecuencia", "Impacto", "M_Critica"]):
            fig2 = px.scatter(
                df,
                x="Frecuencia", y="Impacto",
                color="M_Critica",
                hover_data=["Rol", "Subcausas"],
                labels={"Frecuencia": "Frecuencia (1–5)", "Impacto": "Impacto (1–5)"},
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            # Zona crítica (cuadrante superior derecho)
            fig2.add_shape(
                type="rect", x0=3.5, y0=3.5, x1=5.2, y1=5.2,
                fillcolor="rgba(230,57,70,0.12)",
                line=dict(color="#E63946", dash="dash")
            )
            fig2.add_annotation(
                x=4.75, y=5.1, text="⚠️ Zona crítica",
                showarrow=False, font=dict(color="#E63946", size=11)
            )
            fig2.update_layout(
                height=370,
                xaxis=dict(range=[0.5, 5.5], dtick=1),
                yaxis=dict(range=[0.5, 5.5], dtick=1),
                margin=dict(l=10, r=10, t=40, b=10),
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    # ── Participación por Rol ───────────────────────────────────────
    st.markdown("### 👥 Participación por Rol")
    if "Rol" in df.columns:
        rol_df = df["Rol"].value_counts().reset_index()
        rol_df.columns = ["Rol", "Respuestas"]
        rol_df["% del total"] = (rol_df["Respuestas"] / len(df) * 100).round(1).astype(str) + "%"
        st.dataframe(rol_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Tabla de los 3 Porqués ──────────────────────────────────────
    st.markdown("### 🔍 Análisis de Causa Raíz — Los 3 Porqués")
    st.caption("Filtra por M para enfocar el análisis sistémico del equipo de seguridad.")

    filtro_m = st.multiselect(
        "Filtrar por M:",
        options=df["M_Critica"].unique().tolist() if "M_Critica" in df.columns else [],
        default=[]
    )

    df_filtrado = df[df["M_Critica"].isin(filtro_m)] if filtro_m else df

    cols_tabla = ["Timestamp", "Rol", "M_Critica", "Subcausas", "Porque_1", "Porque_2", "Porque_3_Causa_Raiz"]
    cols_disponibles = [c for c in cols_tabla if c in df_filtrado.columns]

    st.dataframe(
        df_filtrado[cols_disponibles].sort_values("Timestamp", ascending=False),
        use_container_width=True,
        hide_index=True,
        height=320
    )

    # ── Descarga de datos ──────────────────────────────────────────
    st.markdown("---")
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Descargar todos los datos (CSV)",
        data=csv,
        file_name=f"ishikawa_project_mexico_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    cliente = conectar_google()
    if cliente is None:
        st.stop()

    hoja = obtener_o_crear_hoja(cliente)

    tab1, tab2 = st.tabs(["📋 Encuesta Operativa", "📊 Dashboard Interactivo"])

    with tab1:
        mostrar_encuesta(hoja)

    with tab2:
        mostrar_dashboard(hoja)


if __name__ == "__main__":
    main()

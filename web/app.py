"""
app.py
--------
FieldWise Streamlit web app — the farmer/extension-worker-facing
front end for the multi-agent crop health pipeline.

Run with:
    streamlit run web/app.py

Light-themed UI. All reasoning happens in agents/orchestrator.py.
"""

from __future__ import annotations
import os
import sys
import tempfile

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.orchestrator import FieldWiseOrchestrator  # noqa: E402

st.set_page_config(
    page_title="FieldWise — Crop Health Advisor",
    page_icon="🌱",
    layout="centered",
    initial_sidebar_state="collapsed",
)

LLM_MODE = os.environ.get("FIELDWISE_LLM_MODE", "mock")

# ── Custom CSS for light, clean, professional look ─────────────────────────
st.markdown("""
<style>
/* Page background */
.stApp { background-color: #F5FBF8; }

/* Hero banner */
.fw-hero {
    background: linear-gradient(135deg, #0F6E56 0%, #1D9E75 100%);
    border-radius: 16px;
    padding: 32px 36px 28px 36px;
    margin-bottom: 24px;
    box-shadow: 0 4px 20px rgba(15,110,86,0.15);
}
.fw-hero h1 {
    color: #FFFFFF !important;
    font-size: 2.4rem !important;
    font-weight: 800 !important;
    margin: 0 0 6px 0 !important;
    letter-spacing: -0.5px;
}
.fw-hero p {
    color: #B8EDD8 !important;
    font-size: 1.05rem !important;
    margin: 0 !important;
}

/* Section cards */
.fw-card {
    background: #FFFFFF;
    border-radius: 12px;
    padding: 24px 28px;
    margin-bottom: 18px;
    border: 1px solid #D4EDE4;
    box-shadow: 0 2px 8px rgba(15,110,86,0.06);
}
.fw-card-title {
    font-size: 1rem;
    font-weight: 700;
    color: #0F6E56;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Result boxes */
.fw-result-success {
    background: #EDFAF3;
    border-left: 4px solid #0F6E56;
    border-radius: 8px;
    padding: 18px 22px;
    margin: 12px 0;
}
.fw-result-warning {
    background: #FFF8E8;
    border-left: 4px solid #E8A020;
    border-radius: 8px;
    padding: 18px 22px;
    margin: 12px 0;
}
.fw-diagnosis-label {
    font-size: 0.78rem;
    font-weight: 700;
    color: #0F6E56;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 4px;
}
.fw-diagnosis-name {
    font-size: 1.4rem;
    font-weight: 800;
    color: #085041;
    margin-bottom: 8px;
}
.fw-explanation {
    font-size: 0.95rem;
    color: #2d4a3e;
    line-height: 1.6;
}

/* Supplier cards */
.fw-supplier {
    background: #F0FAF5;
    border: 1px solid #C8E8DA;
    border-radius: 10px;
    padding: 14px 18px;
    margin: 8px 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
}
.fw-supplier-product {
    font-weight: 700;
    color: #085041;
    font-size: 0.95rem;
}
.fw-supplier-meta {
    font-size: 0.85rem;
    color: #4a7a65;
}
.fw-price {
    display: inline-block;
    background: #0F6E56;
    color: white;
    border-radius: 20px;
    padding: 2px 12px;
    font-size: 0.8rem;
    font-weight: 600;
    margin-top: 4px;
}

/* Follow-up box */
.fw-followup {
    background: #EEF4FF;
    border: 1px solid #C0D4F5;
    border-radius: 10px;
    padding: 14px 18px;
    margin-top: 8px;
}
.fw-followup-label {
    font-size: 0.78rem;
    font-weight: 700;
    color: #2a4a9a;
    text-transform: uppercase;
    letter-spacing: 1px;
}
.fw-followup-date {
    font-size: 1.1rem;
    font-weight: 700;
    color: #1a2e7a;
    margin: 4px 0 2px 0;
}
.fw-caseid {
    font-size: 0.78rem;
    color: #5a70aa;
    font-family: monospace;
}

/* Pipeline steps */
.fw-pipeline {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin: 10px 0 18px 0;
}
.fw-step {
    background: #E8F5F0;
    border: 1px solid #A8D8C4;
    color: #085041;
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 0.78rem;
    font-weight: 600;
}
.fw-step-arrow {
    color: #A8D8C4;
    font-size: 0.9rem;
    line-height: 26px;
}

/* Mock banner */
.fw-mock {
    background: #FFF8E8;
    border: 1px solid #F0C060;
    border-radius: 10px;
    padding: 10px 16px;
    font-size: 0.85rem;
    color: #7a5010;
    margin-bottom: 18px;
}

/* Submit button */
div.stFormSubmitButton > button {
    background: linear-gradient(135deg, #0F6E56, #1D9E75) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    padding: 12px !important;
    box-shadow: 0 4px 12px rgba(15,110,86,0.3) !important;
    transition: all 0.2s !important;
}
div.stFormSubmitButton > button:hover {
    box-shadow: 0 6px 18px rgba(15,110,86,0.4) !important;
    transform: translateY(-1px) !important;
}

/* Hide streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_orchestrator() -> FieldWiseOrchestrator:
    return FieldWiseOrchestrator()


def render_header() -> None:
    st.markdown("""
    <div class="fw-hero">
        <h1>🌱 FieldWise</h1>
        <p>Multi-agent crop health advisor for smallholder farmers</p>
    </div>
    """, unsafe_allow_html=True)

    if LLM_MODE == "mock":
        st.markdown("""
        <div class="fw-mock">
            🧪 <strong>Demo mode</strong> — running on mock AI responses (free, offline).
            Set <code>FIELDWISE_LLM_MODE=gemini</code> + <code>GEMINI_API_KEY</code> for live diagnosis.
        </div>
        """, unsafe_allow_html=True)

   
    st.markdown("""
    <div class="fw-pipeline">
        <span class="fw-step">📷 Vision</span>
        <span class="fw-step-arrow">→</span>
        <span class="fw-step">🔍 Triage</span>
        <span class="fw-step-arrow">→</span>
        <span class="fw-step">🧠 Diagnosis</span>
        <span class="fw-step-arrow">→</span>
        <span class="fw-step">🛒 Local Resources</span>
        <span class="fw-step-arrow">→</span>
        <span class="fw-step">📅 Follow-up</span>
    </div>
    """, unsafe_allow_html=True)


def render_input_form():
    st.markdown('<div class="fw-card">', unsafe_allow_html=True)
    st.markdown('<div class="fw-card-title">🌿 Describe your crop problem</div>', unsafe_allow_html=True)

    with st.form("case_form"):
        description = st.text_area(
            "What does the crop look like?",
            placeholder="e.g. Leaves have brown spots with yellow rings, starting from the bottom of the plant.",
            height=110,
            help="Describe symptoms in your own words — spots, color changes, insects, wilting, etc.",
        )

        photo = st.file_uploader(
            "📷 Upload a photo of the affected crop (optional)",
            type=["jpg", "jpeg", "png"],
            help="A phone photo works perfectly. The Vision Agent will analyze visible symptoms.",
        )

        col1, col2 = st.columns(2)
        with col1:
            farmer_id = st.text_input(
                "Farmer / Field ID",
                value="demo_farmer_001",
                help="Use a pseudonymous ID — not a real name or phone number.",
            )
        with col2:
            region = st.text_input(
                "Region",
                value="vijayawada",
                help="Used to find nearby suppliers.",
            )

        submitted = st.form_submit_button("🔍 Get Advice", use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)
    return submitted, description, photo, farmer_id, region


def render_trace(trace: list[str]) -> None:
    with st.expander("🔍 See how the agents reached this result"):
        for line in trace:
            st.markdown(
                f'<p style="font-size:0.82rem;color:#4a7a65;font-family:monospace;margin:2px 0">{line}</p>',
                unsafe_allow_html=True,
            )


def render_report(report) -> None:
    if report.escalated:
        st.markdown("""
        <div class="fw-result-warning">
            <div style="font-size:1.1rem;font-weight:700;color:#7a5010;margin-bottom:6px">
                ⚠️ This case needs a human expert
            </div>
            <div style="font-size:0.92rem;color:#5a3a08;line-height:1.6">
                FieldWise wasn't confident enough to give automated advice here.
                Rather than guess, it's flagged this for review by a human agricultural expert.
                This is a deliberate safety feature, not a limitation.
            </div>
        </div>
        """, unsafe_allow_html=True)
        render_trace(report.trace)
        return

    # Diagnosis result
    st.markdown(f"""
    <div class="fw-result-success">
        <div class="fw-diagnosis-label">✅ Diagnosis</div>
        <div class="fw-diagnosis-name">{report.diagnosis}</div>
        <div class="fw-explanation">{report.explanation}</div>
    </div>
    """, unsafe_allow_html=True)

    
    if report.treatment_options:
        st.markdown('<div class="fw-card-title" style="margin-top:20px">🛒 Locally available treatment</div>',
                    unsafe_allow_html=True)
        for opt in report.treatment_options:
            st.markdown(f"""
            <div class="fw-supplier">
                <div class="fw-supplier-product">💊 {opt['product']}</div>
                <div class="fw-supplier-meta">
                    🏪 {opt['supplier_name']} &nbsp;·&nbsp; 📍 {opt['distance_km']} km away
                </div>
                <span class="fw-price">{opt['approx_price']}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No local supplier data found for this region yet.")

    
    st.markdown(f"""
    <div class="fw-followup" style="margin-top:20px">
        <div class="fw-followup-label">📅 Follow-up schedule</div>
        <div class="fw-followup-date">Re-check your crop on {report.next_check_date}</div>
        <div class="fw-caseid">Case ID: {report.case_id}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    render_trace(report.trace)


def main() -> None:
    render_header()
    submitted, description, photo, farmer_id, region = render_input_form()

    if not submitted:
        
        st.markdown("""
        <div class="fw-card" style="margin-top: 8px;">
            <div class="fw-card-title">💡 How it works</div>
            <div style="font-size:0.9rem; color:#2d4a3e; line-height:1.8;">
                <b>1.</b> Describe what you see on your crop — spots, color changes, insects, wilting.<br>
                <b>2.</b> Optionally upload a phone photo for visual analysis.<br>
                <b>3.</b> Five specialized AI agents analyze your case in sequence.<br>
                <b>4.</b> Get a specific diagnosis, nearby suppliers with prices, and a follow-up date.<br>
                <b>5.</b> If the system isn't confident enough, it says so — and recommends a human expert.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    if not description.strip():
        st.error("Please describe what you're seeing before submitting.")
        return

    image_path = None
    if photo is not None:
        suffix = os.path.splitext(photo.name)[1] or ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(photo.getbuffer())
            image_path = tmp.name

    orchestrator = get_orchestrator()

    with st.spinner("🌿 Running multi-agent diagnosis pipeline..."):
        report = orchestrator.process_case(
            description=description,
            farmer_id=farmer_id or "anonymous",
            region=region or "default",
            image_path=image_path,
        )

    
    if image_path:
        os.unlink(image_path)

    render_report(report)


if __name__ == "__main__":
    main()

import streamlit as st
import requests
import json
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Intelligent Networking Assistant",
    page_icon="🤝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Backend Base URL
API_BASE_URL = "http://127.0.0.1:8000/api"

# Inject beautiful CSS for modern styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Outfit', sans-serif !important;
}

.gradient-title {
    background: linear-gradient(135deg, #6366f1, #a855f7, #ec4899);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700;
    font-size: 2.4rem;
    margin-bottom: 0.3rem;
    text-align: left;
}

.subtitle {
    color: #94a3b8;
    font-size: 1.05rem;
    margin-bottom: 1.8rem;
}

.custom-card {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    color: #ffffff !important;
}
.custom-card p, .custom-card span {
    color: #ffffff !important;
}
.custom-card:hover {
    border-color: #6366f1;
    box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.15);
}

.theme-badge {
    background: linear-gradient(135deg, #4f46e5, #7c3aed);
    color: #ffffff;
    padding: 5px 12px;
    border-radius: 20px;
    font-weight: 500;
    font-size: 0.82rem;
    display: inline-block;
    margin-right: 6px;
    margin-bottom: 8px;
}

.interest-badge {
    background: #0f172a;
    border: 1px solid #6366f1;
    color: #a5b4fc;
    padding: 4px 10px;
    border-radius: 14px;
    font-size: 0.78rem;
    display: inline-block;
    margin-right: 6px;
    margin-bottom: 6px;
}

.verified-badge {
    background-color: rgba(34, 197, 94, 0.15);
    color: #4ade80;
    border: 1px solid rgba(34, 197, 94, 0.3);
    padding: 5px 12px;
    border-radius: 8px;
    font-size: 0.85rem;
    font-weight: 600;
    display: inline-block;
}

.partial-badge {
    background-color: rgba(234, 179, 8, 0.15);
    color: #facc15;
    border: 1px solid rgba(234, 179, 8, 0.3);
    padding: 5px 12px;
    border-radius: 8px;
    font-size: 0.85rem;
    font-weight: 600;
    display: inline-block;
}

.unverified-badge {
    background-color: rgba(239, 68, 68, 0.15);
    color: #f87171;
    border: 1px solid rgba(239, 68, 68, 0.3);
    padding: 5px 12px;
    border-radius: 8px;
    font-size: 0.85rem;
    font-weight: 600;
    display: inline-block;
}

.citation-box {
    background-color: rgba(15, 23, 42, 0.6);
    border-left: 3px solid #8b5cf6;
    border-radius: 0 8px 8px 0;
    padding: 10px 14px;
    margin-top: 10px;
    font-size: 0.88rem;
    color: #cbd5e1 !important;
}

.wiki-card {
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.85), rgba(30, 41, 59, 0.95));
    border: 1px solid #0284c7;
    border-radius: 10px;
    padding: 14px 18px;
    margin-top: 12px;
    margin-bottom: 14px;
    box-shadow: 0 4px 12px rgba(2, 132, 199, 0.15);
}

.wiki-btn {
    display: inline-block;
    background: #0284c7;
    color: #ffffff !important;
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 0.85rem;
    font-weight: 600;
    text-decoration: none;
    transition: background 0.2s;
    margin-top: 6px;
}
.wiki-btn:hover {
    background: #0369a1;
    color: #ffffff !important;
}

.separator {
    height: 1px;
    background: linear-gradient(90deg, transparent, #334155, transparent);
    margin: 20px 0;
}
</style>
""", unsafe_allow_html=True)

# Helper function to check backend health
def check_backend():
    try:
        res = requests.get("http://127.0.0.1:8000/", timeout=2)
        return res.status_code == 200
    except Exception:
        return False

# Helper functions for API calls
def fetch_users():
    try:
        res = requests.get(f"{API_BASE_URL}/users", timeout=3)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return []

def fetch_documents():
    try:
        res = requests.get(f"{API_BASE_URL}/knowledge/documents", timeout=3)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return []

def fetch_conversations(user_id=None):
    try:
        params = {"user_id": user_id} if user_id else {}
        res = requests.get(f"{API_BASE_URL}/conversations", params=params, timeout=3)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return []

# Sidebar Navigation
with st.sidebar:
    st.markdown('<h2 style="font-weight:700; margin-bottom:15px;">🤝 Intelligent Assistant</h2>', unsafe_allow_html=True)
    
    # Active User Persona Selector
    users = fetch_users()
    user_options = {u["name"] + f" ({u['role']})": u for u in users} if users else {}
    selected_user_name = None
    active_user = None

    if user_options:
        selected_user_label = st.selectbox("Active Persona", list(user_options.keys()))
        active_user = user_options[selected_user_label]
        st.caption(f"🎯 **Goal:** {active_user.get('networking_goal', 'Networking')}")
        st.caption(f"🛠️ **Tech:** {active_user.get('technical_background', '')}")

    st.markdown("---")
    menu = st.radio(
        "Modules",
        [
            "💬 Professional Generator",
            "🔍 Knowledge Verification",
            "📚 Knowledge Repository",
            "👤 User Persona Manager",
            "💡 Smart Recommendations",
            "📊 Analytics & Evaluation",
            "📜 Legacy Starter Generator"
        ],
        index=0
    )

if not check_backend():
    st.error("⚠️ Cannot connect to the FastAPI backend server on http://127.0.0.1:8000!")
    st.markdown("""
    Please make sure the backend is running with:
    ```powershell
    .\\.venv\\Scripts\\uvicorn backend.main:app --reload
    ```
    """)
    st.stop()

# =========================================================================
# MODULE 2 & 6: PROFESSIONAL CONVERSATION GENERATOR (RAG + EXPLAINABLE AI)
# =========================================================================
if menu == "💬 Professional Generator":
    st.markdown('<h1 class="gradient-title">Personalized Professional Generator</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Generate persona-conditioned, RAG-grounded professional messages verified against curated knowledge.</p>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 📝 Input Parameters")
        with st.form("convo_generator_form"):
            convo_type = st.selectbox(
                "Conversation Modality",
                [
                    ("linkedin_invitation", "LinkedIn Connection Request (<300 chars)"),
                    ("follow_up_email", "Post-Event / Meeting Follow-up Email"),
                    ("interview_reply", "Interview Thank-You & Technical Follow-up"),
                    ("technical_discussion", "Technical Discussion Contribution"),
                    ("event_icebreaker", "Conference Event Icebreakers")
                ],
                format_func=lambda x: x[1]
            )
            recipient_name = st.text_input("Recipient Name", value="Alex Morgan")
            recipient_role = st.text_input("Recipient Role / Title", value="Senior Engineering Director")
            topic = st.text_input("Core Topic / Shared Context", value="Retrieval-Augmented Generation & Distributed AI")
            specific_note = st.text_area("Optional Personal Details / Niche Context", value="", placeholder="e.g. We briefly spoke at the AI summit about vector search latency.", height=80)
            use_rag = st.checkbox("Ground in Knowledge Repository (RAG)", value=True, help="Retrieves relevant evidence from uploaded documents using FAISS and BM25 to prevent hallucinations.")

            submit_btn = st.form_submit_button("Generate Verified Message")

    if submit_btn:
        with col2:
            try:
                payload = {
                    "user_id": active_user["id"] if active_user else None,
                    "conversation_type": convo_type[0],
                    "recipient_name": recipient_name,
                    "recipient_role": recipient_role,
                    "topic": topic,
                    "specific_note": specific_note,
                    "use_rag": use_rag
                }
                res = requests.post(f"{API_BASE_URL}/conversations/generate", json=payload)
                if res.status_code == 200:
                    st.session_state["latest_convo"] = res.json()
                    st.success("Generation & verification complete!")
                else:
                    st.error(f"Error {res.status_code}: {res.text}")
            except Exception as e:
                st.error(f"Request failed: {e}")

    with col2:
        if "latest_convo" in st.session_state:
            data = st.session_state["latest_convo"]
            st.markdown(f"### 🎯 {data.get('title', 'Generated Message')}")

            # Confidence and Verification Status Badge
            conf = data.get("confidence_score", 0.85)
            status = data.get("verification_status", "VERIFIED")
            badge_class = "verified-badge" if status == "VERIFIED" else "partial-badge" if status == "PARTIALLY_SUPPORTED" else "unverified-badge"
            st.markdown(f'<span class="{badge_class}">Status: {status} • Confidence: {int(conf*100)}%</span>', unsafe_allow_html=True)

            # Generated Content Card
            st.markdown(f"""
            <div class="custom-card" style="margin-top:14px;">
                <pre style="white-space: pre-wrap; font-family: inherit; font-size: 0.98rem; line-height: 1.6; margin: 0; color: #f8fafc;">{data.get('generated_content')}</pre>
            </div>
            """, unsafe_allow_html=True)

            # Explainable AI Rationale
            if data.get("rationale"):
                st.markdown("##### 💡 Explainable AI Rationale")
                st.info(data["rationale"])

            # Citations / Grounded Sources
            if data.get("sources"):
                st.markdown("##### 📚 Corroborated Sources & Citations")
                for s in data["sources"]:
                    src_name = s.get("name") or s.get("source") or "Reference Document"
                    snippet = s.get("snippet", "")
                    st.markdown(f"""
                    <div class="citation-box">
                        <strong>📌 {src_name}</strong>: <em>"{snippet}"</em>
                    </div>
                    """, unsafe_allow_html=True)

            # Thumbs Up / Down Feedback
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            col_f1, col_f2, col_f3 = st.columns([1, 1, 4])
            with col_f1:
                if st.button("👍 Useful", key=f"convo_up_{data['id']}"):
                    requests.post(f"{API_BASE_URL}/conversations/{data['id']}/feedback", json={"feedback": True})
                    st.toast("Marked as helpful strategy!")
            with col_f2:
                if st.button("👎 Not Useful", key=f"convo_down_{data['id']}"):
                    requests.post(f"{API_BASE_URL}/conversations/{data['id']}/feedback", json={"feedback": False})
                    st.toast("Feedback recorded.")

# =========================================================================
# MODULE 5: KNOWLEDGE VERIFICATION ENGINE
# =========================================================================
elif menu == "🔍 Knowledge Verification":
    st.markdown('<h1 class="gradient-title">Knowledge Verification Engine</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Audit technical claims and statements against internal documents and Wikipedia with semantic similarity & confidence scoring.</p>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 🔎 Claim to Verify")
        claim_input = st.text_area(
            "Enter statement, assertion, or conversation paragraph",
            value="Retrieval-Augmented Generation grounds large language models in verified external documents to reduce hallucinations.",
            height=130
        )
        include_wiki = st.checkbox("Query Wikipedia for external validation", value=True)
        verify_btn = st.button("Run Knowledge Verification Engine")

    if verify_btn and claim_input.strip():
        with col2:
            try:
                payload = {"claim": claim_input.strip(), "check_wiki": include_wiki}
                res = requests.post(f"{API_BASE_URL}/verify/knowledge", json=payload)
                if res.status_code == 200:
                    st.session_state["verification_result"] = res.json()
                    st.success("Verification complete!")
                else:
                    st.error(f"Error {res.status_code}: {res.text}")
            except Exception as e:
                st.error(f"Verification request failed: {e}")

    with col2:
        if "verification_result" in st.session_state:
            vdata = st.session_state["verification_result"]
            verdict = vdata.get("verdict", "UNVERIFIED")
            score_pct = vdata.get("confidence_pct", 0)

            badge_class = "verified-badge" if verdict == "VERIFIED" else "partial-badge" if verdict == "PARTIALLY_SUPPORTED" else "unverified-badge"
            st.markdown(f'<span class="{badge_class}">Verdict: {verdict} • Confidence: {score_pct}%</span>', unsafe_allow_html=True)

            st.markdown(f"""
            <div class="custom-card" style="margin-top:14px;">
                <p><strong>Claim:</strong> <em>"{vdata.get('claim')}"</em></p>
                <div class="separator"></div>
                <p style="color:#a5b4fc !important;"><strong>Justification:</strong> {vdata.get('explanation')}</p>
            </div>
            """, unsafe_allow_html=True)

            sources = vdata.get("sources", [])
            if sources:
                st.markdown("##### 📑 Retrieved Evidence & Citations")
                for s in sources:
                    sim_pct = int(s.get("similarity", 0.0) * 100)
                    url_link = f" • <a href='{s.get('url')}' target='_blank' style='color:#818cf8;'>Open Link ↗</a>" if s.get('url') else ""
                    st.markdown(f"""
                    <div class="citation-box">
                        <strong>{s.get('type')}: {s.get('name')}</strong> (Match: {sim_pct}%){url_link}<br>
                        <em>"{s.get('snippet')}"</em>
                    </div>
                    """, unsafe_allow_html=True)

# =========================================================================
# MODULE 3 & 4: KNOWLEDGE REPOSITORY & SEMANTIC SEARCH
# =========================================================================
elif menu == "📚 Knowledge Repository":
    st.markdown('<h1 class="gradient-title">Knowledge Repository & Vector Search</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Upload organizational documents (PDF, DOCX, PPTX, TXT) and inspect FAISS + BM25 hybrid indexing.</p>', unsafe_allow_html=True)

    tab_upload, tab_search, tab_docs = st.tabs(["📤 Upload Documents", "🔍 Hybrid Vector Search", "📂 Ingested Documents"])

    with tab_upload:
        col_u1, col_u2 = st.columns([1, 1])
        with col_u1:
            st.markdown("### 📤 Upload New Document")
            uploaded_file = st.file_uploader("Choose a file (.pdf, .docx, .pptx, .txt)", type=["pdf", "docx", "pptx", "txt", "md"])
            if uploaded_file is not None:
                if st.button("Parse & Ingest into Vector Index"):
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    res = requests.post(f"{API_BASE_URL}/knowledge/upload", files=files)
                    if res.status_code == 200:
                        st.success(res.json().get("message", "Document successfully indexed!"))
                        st.rerun()
                    else:
                        st.error(f"Upload failed: {res.text}")
        with col_u2:
            st.info("""
            **Supported Formats:**
            - 📄 **PDF** (Extracts text page-by-page via `pypdf`)
            - 📝 **Word (.docx)** (Extracts paragraphs & tables via `python-docx`)
            - 📊 **PowerPoint (.pptx)** (Extracts slide shapes via `python-pptx`)
            - 📜 **Plain Text / Markdown** (.txt, .md)

            **Processing Pipeline:**
            1. Document parsing → 2. Semantic text chunking → 3. Dense embedding via SBERT → 4. FAISS index build + BM25 corpus update.
            """)

    with tab_search:
        st.markdown("### 🔎 Hybrid Semantic Search (FAISS + BM25)")
        query = st.text_input("Enter search query or technical concept", value="Transformer architecture and latency")
        top_k = st.slider("Results count (Top K)", min_value=1, max_value=8, value=3)
        if st.button("Execute Hybrid Search"):
            res = requests.post(f"{API_BASE_URL}/knowledge/search", json={"query": query, "top_k": top_k, "hybrid": True})
            if res.status_code == 200:
                results = res.json()
                if not results:
                    st.warning("No matching chunks found.")
                for idx, r in enumerate(results):
                    st.markdown(f"""
                    <div class="custom-card">
                        <h4 style="color:#a855f7; margin-top:0;">#{idx+1} {r['document_name']} (Chunk {r['chunk_index']})</h4>
                        <p style="font-size:0.92rem; line-height:1.5;">{r['text']}</p>
                        <span class="theme-badge">Cosine Similarity: {round(r['score'], 3)}</span>
                        <span class="interest-badge">RRF Rank Score: {round(r['rrf_score'], 4)}</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.error(f"Search failed: {res.text}")

    with tab_docs:
        docs = fetch_documents()
        st.markdown(f"### 📚 Ingested Documents ({len(docs)} files)")
        if not docs:
            st.info("No documents currently in the repository. Head over to the 'Upload Documents' tab to ingest files!")
        else:
            for d in docs:
                dt = datetime.fromisoformat(d["created_at"]).strftime("%b %d, %Y %I:%M %p") if d.get("created_at") else "N/A"
                with st.expander(f"📄 {d['filename']} • {d['chunk_count']} chunks • {d['file_type'].upper()}"):
                    st.write(f"**Uploaded:** {dt} | **File Size:** {round(d['file_size']/1024, 1)} KB | **Document ID:** #{d['id']}")
                    
                    col_b1, col_b2, col_b3 = st.columns([2, 2, 5])
                    with col_b1:
                        show_chunks = st.button("🔍 View Chunks", key=f"view_chunks_{d['id']}")
                    with col_b2:
                        if st.button("🗑️ Delete Document", key=f"del_doc_{d['id']}", type="secondary"):
                            del_res = requests.delete(f"{API_BASE_URL}/knowledge/documents/{d['id']}")
                            if del_res.status_code == 200:
                                st.success(f"Deleted '{d['filename']}' successfully!")
                                st.rerun()
                            else:
                                st.error(f"Failed to delete: {del_res.text}")

                    if show_chunks:
                        c_res = requests.get(f"{API_BASE_URL}/knowledge/documents/{d['id']}/chunks")
                        if c_res.status_code == 200:
                            chunks = c_res.json()
                            for c in chunks:
                                st.text_area(f"Chunk #{c['chunk_index']} (ID: {c['id']})", c["text_content"], height=90)

# =========================================================================
# MODULE 1: USER PERSONA MANAGER
# =========================================================================
elif menu == "👤 User Persona Manager":
    st.markdown('<h1 class="gradient-title">User Persona & Profile Management</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Define user profiles to steer personalized tone, technical background, and networking objectives.</p>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### ➕ Create New Profile")
        with st.form("new_user_form"):
            new_name = st.text_input("Full Name", value="Jane Doe")
            new_email = st.text_input("Email", value="jane.doe@example.com")
            new_role = st.selectbox("Professional Role", [
                "Software Engineer",
                "Machine Learning Engineer",
                "AI Researcher",
                "Product Manager",
                "Engineering Lead / Director",
                "Student / Aspiring Engineer",
                "Technical Recruiter"
            ])
            new_level = st.selectbox("Experience Level", ["Junior", "Mid-Level", "Senior", "Lead / Principal", "Executive"])
            new_tech = st.text_input("Technical Background / Skills", value="Python, Go, Kubernetes, Cloud Architecture")
            new_goal = st.selectbox("Primary Networking Objective", [
                "Career Growth & Job Seeking",
                "Research & Technical Collaboration",
                "Mentorship & Guidance",
                "Industry Knowledge Sharing",
                "Talent Acquisition & Recruiting"
            ])
            create_btn = st.form_submit_button("Save Profile")

        if create_btn:
            payload = {
                "name": new_name,
                "email": new_email,
                "role": new_role,
                "experience_level": new_level,
                "technical_background": new_tech,
                "networking_goal": new_goal
            }
            res = requests.post(f"{API_BASE_URL}/users", json=payload)
            if res.status_code == 200:
                st.success("User profile created successfully!")
                st.rerun()
            else:
                st.error(f"Creation failed: {res.text}")

    with col2:
        st.markdown("### 👥 Existing Profiles")
        users = fetch_users()
        for u in users:
            st.markdown(f"""
            <div class="custom-card">
                <h4 style="color:#a855f7; margin-top:0;">{u['name']}</h4>
                <p><strong>Role:</strong> {u['role']} ({u['experience_level']})</p>
                <p><strong>Goal:</strong> {u['networking_goal']}</p>
                <p><strong>Tech Stack:</strong> <span style="color:#cbd5e1;">{u['technical_background']}</span></p>
            </div>
            """, unsafe_allow_html=True)

# =========================================================================
# MODULE 7: SMART RECOMMENDATIONS
# =========================================================================
elif menu == "💡 Smart Recommendations":
    st.markdown('<h1 class="gradient-title">Smart Networking Recommendations</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Proactive topics, connection strategies, and questions adapted to your career level and learned from positive feedback.</p>', unsafe_allow_html=True)

    user_id = active_user["id"] if active_user else None
    res = requests.get(f"{API_BASE_URL}/recommendations", params={"user_id": user_id})
    if res.status_code == 200:
        recs = res.json()
        
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("### 🎯 Recommended Discussion Topics")
            for t in recs.get("recommended_topics", []):
                st.markdown(f"""
                <div class="custom-card">
                    <h4 style="color:#818cf8; margin-top:0;">{t['title']}</h4>
                    <p style="font-size:0.9rem;">{t['reason']}</p>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("### 🧭 Strategic Networking Guidance")
            strat = recs.get("strategy_guidance", {})
            st.markdown(f"""
            <div class="custom-card" style="border-left:4px solid #a855f7;">
                <p><strong>Mindset:</strong> {strat.get('mindset')}</p>
                <p><strong>Action Item:</strong> {strat.get('action_item')}</p>
                <p><strong>Follow-Up Window:</strong> <span class="interest-badge">{strat.get('follow_up_window')}</span></p>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown("### 💬 Proven High-Impact Starters (Learned from Feedback)")
            for starter in recs.get("proven_starters", []):
                st.markdown(f"""
                <div class="custom-card">
                    <p style="font-style:italic;">"{starter}"</p>
                    <span class="verified-badge">👍 High Positive Rating</span>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("### ❓ Impactful Questions to Ask")
            for q in recs.get("recommended_questions", []):
                st.markdown(f"""
                <div style="background-color:rgba(15,23,42,0.4); border-left:3px solid #6366f1; padding:10px 14px; margin-bottom:8px; border-radius:0 6px 6px 0;">
                    <span style="font-size:0.92rem; color:#e2e8f0;">"{q}"</span>
                </div>
                """, unsafe_allow_html=True)

# =========================================================================
# MODULE 8: ANALYTICS DASHBOARD & OBJECTIVE EVALUATION BENCHMARK
# =========================================================================
elif menu == "📊 Analytics & Evaluation":
    st.markdown('<h1 class="gradient-title">Analytics & Objective Evaluation</h1>', unsafe_allow_html=True)

    tab_metrics, tab_eval = st.tabs(["📈 Platform Metrics", "🧪 Objective Evaluation Benchmark (BLEU / chrF / ROUGE)"])

    with tab_metrics:
        res = requests.get(f"{API_BASE_URL}/analytics/overview")
        if res.status_code == 200:
            stats = res.json()
            
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Total Conversations", stats.get("total_conversations", 0))
            with c2:
                st.metric("Satisfaction Rate", f"{stats.get('satisfaction_rate', 100)}%")
            with c3:
                st.metric("Knowledge Chunks Indexed", stats.get("total_chunks", 0))
            with c4:
                st.metric("Avg Fact Confidence", f"{stats.get('average_confidence', 0)}%")

            st.markdown("<div class='separator'></div>", unsafe_allow_html=True)

            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.markdown("### 👍 Feedback Distribution")
                st.write(f"**Useful Strategies (Thumbs Up):** {stats.get('thumbs_up', 0)}")
                st.write(f"**Needs Improvement (Thumbs Down):** {stats.get('thumbs_down', 0)}")
                st.progress(stats.get("satisfaction_rate", 100) / 100.0)

            with col_m2:
                st.markdown("### 🗂️ Conversation Types Breakdown")
                types = stats.get("conversation_types", {})
                if types:
                    for k, v in types.items():
                        st.write(f"• **{k.replace('_', ' ').title()}:** {v}")
                else:
                    st.info("No generated conversations logged yet.")

    with tab_eval:
        st.markdown("### 🧪 Objective Evaluation Suite (BLEU, chrF, ROUGE)")
        st.caption("Benchmark candidate generation against curated professional gold-standard communication sets.")

        candidate = st.text_area(
            "Candidate Message to Evaluate",
            value="Hi Alex, I came across your work on distributed AI systems and found your recent architecture insights compelling. I would love to connect and follow your journey.",
            height=100
        )
        eval_convo_type = st.selectbox(
            "Evaluation Benchmark Domain",
            ["linkedin_invitation", "follow_up_email", "interview_reply", "technical_discussion", "event_icebreaker"]
        )

        if st.button("Compute Benchmark Metrics"):
            eval_res = requests.post(
                f"{API_BASE_URL}/evaluation/benchmark",
                json={"candidate_text": candidate, "conversation_type": eval_convo_type}
            )
            if eval_res.status_code == 200:
                metrics = eval_res.json()
                
                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    st.metric("SacreBLEU", f"{metrics['bleu']}")
                with m2:
                    st.metric("chrF F-score", f"{metrics['chrf']}")
                with m3:
                    st.metric("ROUGE-1 F1", f"{metrics['rouge1']}%")
                with m4:
                    st.metric("ROUGE-L F1", f"{metrics['rougeL']}%")

                st.markdown(f"""
                <div class="custom-card" style="margin-top:15px;">
                    <h4 style="color:#a855f7; margin-top:0;">📊 Benchmark Interpretation</h4>
                    <p>{metrics.get('interpretation')}</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error(f"Evaluation failed: {eval_res.text}")

# =========================================================================
# LEGACY STARTER GENERATOR (BACKWARD COMPATIBILITY)
# =========================================================================
elif menu == "📜 Legacy Starter Generator":
    st.markdown('<h1 class="gradient-title">Conference Event Starters</h1>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])
    with col1:
        with st.form("legacy_starter_form"):
            event_desc = st.text_area("Event Description", value="AI for Sustainable Cities. Discussing climate change, smart infrastructure, and urban planning solutions.", height=130)
            interests_in = st.text_input("Your Interests", value="climate change, machine learning")
            btn = st.form_submit_button("Generate Starters")

    if btn and event_desc.strip():
        with col2:
            interests = [i.strip() for i in interests_in.split(",") if i.strip()]
            res = requests.post(f"{API_BASE_URL}/suggestions", json={"event_description": event_desc, "interests": interests})
            if res.status_code == 200:
                sdata = res.json()
                st.markdown("### 🎯 Generated Results")
                for t in sdata["themes"]:
                    st.markdown(f'<span class="theme-badge">{t}</span>', unsafe_allow_html=True)
                for s in sdata["starters"]:
                    st.markdown(f'<div class="custom-card"><p><em>"{s}"</em></p></div>', unsafe_allow_html=True)
            else:
                st.error(f"Failed: {res.text}")
import datetime
import io
import json
import re
import sqlite3
import uuid
import pandas as pd
from pypdf import PdfReader
import streamlit as st

# Configure page settings
st.set_page_config(
    page_title="Enterprise Talent Acquisition Portal",
    page_icon="🏢",
    layout="centered",
    initial_sidebar_state="expanded",
)

# Standardized compensation options shared across sliders
CTC_OPTIONS = [
    "< 6 LPA",
    "6-12 LPA",
    "12-20 LPA",
    "20-35 LPA",
    "35-50 LPA",
    "50+ LPA",
]

# ----------------- Database Setup & Persistence ----------------- #
DB_FILE = "applicant_portal.db"


def init_db():
  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()
  c.execute("""
        CREATE TABLE IF NOT EXISTS applicants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id TEXT UNIQUE,
            timestamp TEXT,
            full_name TEXT,
            email TEXT,
            phone TEXT,
            dob TEXT,
            age INTEGER,
            gender TEXT,
            country TEXT,
            current_city TEXT,
            current_company TEXT,
            primary_role TEXT,
            experience_years INTEGER,
            work_preference TEXT,
            current_ctc TEXT,
            expected_ctc TEXT,
            notice_period TEXT,
            skills TEXT,
            linkedin_url TEXT,
            portfolio_url TEXT,
            highest_education TEXT,
            college_name TEXT,
            passing_year INTEGER,
            background_check_consent INTEGER,
            non_compete_acknowledged INTEGER,
            data_privacy_consent INTEGER,
            declaration_signed INTEGER,
            resume_uploaded INTEGER
        )
    """)
  conn.commit()
  conn.close()


def save_final_applicant(data: dict):
  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()

  # Always generate a globally unique Application ID upon submission
  unique_app_id = (
      f"APP-{datetime.datetime.now().strftime('%y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
  )
  data["app_id"] = unique_app_id

  # Use INSERT OR REPLACE to guarantee no SQLite IntegrityError crashes
  c.execute(
      """
        INSERT OR REPLACE INTO applicants (
            application_id, timestamp, full_name, email, phone, dob, age,
            gender, country, current_city, current_company, primary_role,
            experience_years, work_preference, current_ctc, expected_ctc,
            notice_period, skills, linkedin_url, portfolio_url, highest_education,
            college_name, passing_year, background_check_consent, non_compete_acknowledged,
            data_privacy_consent, declaration_signed, resume_uploaded
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
      (
          unique_app_id,
          datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
          data.get("full_name"),
          data.get("email"),
          data.get("phone"),
          data.get("dob"),
          data.get("age"),
          data.get("gender"),
          data.get("country"),
          data.get("current_city"),
          data.get("current_company"),
          data.get("primary_role"),
          data.get("experience_years"),
          data.get("work_preference"),
          data.get("current_ctc"),
          data.get("expected_ctc"),
          data.get("notice_period"),
          json.dumps(data.get("skills", [])),
          data.get("linkedin_url"),
          data.get("portfolio_url"),
          data.get("highest_education"),
          data.get("college_name"),
          data.get("passing_year"),
          1 if data.get("bg_consent") else 0,
          1 if data.get("nc_ack") else 0,
          1 if data.get("dp_consent") else 0,
          1 if data.get("declaration") else 0,
          1 if data.get("resume_uploaded") else 0,
      ),
  )
  conn.commit()
  conn.close()


def load_all_applicants() -> pd.DataFrame:
  conn = sqlite3.connect(DB_FILE)
  df = pd.read_sql_query("SELECT * FROM applicants ORDER BY id DESC", conn)
  conn.close()
  return df


init_db()


# ----------------- CV Extraction Engine ----------------- #
def parse_resume(uploaded_file):
  extracted_text = ""
  try:
    if uploaded_file.name.endswith(".pdf"):
      reader = PdfReader(uploaded_file)
      for page in reader.pages:
        txt = page.extract_text()
        if txt:
          extracted_text += txt + "\n"
    elif uploaded_file.name.endswith(".txt"):
      extracted_text = uploaded_file.read().decode("utf-8")
  except Exception as e:
    st.error(f"Error reading resume: {e}")
    return {}

  data = {}
  email_match = re.search(
      r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", extracted_text
  )
  if email_match:
    data["email"] = email_match.group(0)

  phone_match = re.search(
      r"(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}",
      extracted_text,
  )
  if phone_match:
    data["phone"] = phone_match.group(0).strip()

  li_match = re.search(
      r"(https?://)?(www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+", extracted_text
  )
  if li_match:
    data["linkedin_url"] = li_match.group(0)

  lines = [
      line.strip()
      for line in extracted_text.split("\n")
      if len(line.strip()) > 2
  ]
  if lines:
    candidate_name = lines[0]
    if len(candidate_name.split()) <= 4 and not re.search(
        r"@|http|resume|curriculum", candidate_name, re.I
    ):
      data["full_name"] = candidate_name

  all_skills = [
      "Python",
      "FastAPI",
      "SQL",
      "Docker",
      "Kubernetes",
      "AWS",
      "Machine Learning",
      "Streamlit",
      "Pandas",
      "PyTorch",
      "Git",
      "Power BI",
  ]
  matched_skills = [
      s for s in all_skills if re.search(rf"\b{re.escape(s)}\b", extracted_text, re.I)
  ]
  if matched_skills:
    data["skills"] = matched_skills

  return data


# ----------------- Session State Initialization ----------------- #
if "current_step" not in st.session_state:
  st.session_state.current_step = 1

# Age Synchronization Setup
if "age_number" not in st.session_state:
  st.session_state.age_number = 25

if "age_slider" not in st.session_state:
  st.session_state.age_slider = 25


def update_from_number():
  st.session_state.age_slider = st.session_state.age_number


def update_from_slider():
  st.session_state.age_number = st.session_state.age_slider


if "form_data" not in st.session_state:
  st.session_state.form_data = {
      "app_id": "DRAFT-APPLICATION",
      "full_name": "",
      "email": "",
      "phone": "",
      "dob": datetime.date(1996, 1, 1),
      "gender": "Male",
      "country": "India",
      "current_city": "",
      "current_company": "",
      "primary_role": "Backend Engineer (FastAPI / Python)",
      "experience_years": 3,
      "work_preference": "Hybrid",
      "current_ctc": "6-12 LPA",
      "expected_ctc": "12-20 LPA",
      "notice_period": "30 Days",
      "skills": ["Python", "FastAPI"],
      "linkedin_url": "",
      "portfolio_url": "",
      "highest_education": "B.Tech / B.E.",
      "college_name": "",
      "passing_year": 2018,
      "bg_consent": False,
      "nc_ack": False,
      "dp_consent": False,
      "declaration": False,
      "resume_uploaded": False,
  }

# Guard against invalid CTC values from older runs
if st.session_state.form_data.get("current_ctc") not in CTC_OPTIONS:
  st.session_state.form_data["current_ctc"] = "6-12 LPA"
if st.session_state.form_data.get("expected_ctc") not in CTC_OPTIONS:
  st.session_state.form_data["expected_ctc"] = "12-20 LPA"


def go_to_step(step_idx):
  st.session_state.current_step = step_idx


# ----------------- Visual Styling ----------------- #
st.markdown(
    """
    <style>
    .stApp {
        background: radial-gradient(circle at 10% 10%, #e0f2fe 0%, transparent 35%),
                    radial-gradient(circle at 90% 90%, #ede9fe 0%, transparent 35%),
                    linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        color: #0f172a;
    }
    .header-box {
        background: #ffffff;
        padding: 24px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 24px;
    }
    .portal-title {
        font-size: 2rem;
        font-weight: 800;
        color: #0369a1;
        margin-bottom: 2px;
    }
    .portal-subtitle {
        color: #64748b;
        font-size: 0.95rem;
    }
    .section-badge {
        display: inline-block;
        padding: 4px 12px;
        background: #e0f2fe;
        color: #0284c7;
        font-weight: 700;
        border-radius: 20px;
        font-size: 0.85rem;
        margin-bottom: 12px;
    }
    div.stButton > button[kind="primary"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 10px 24px !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Top Bar Header
st.markdown(
    f"""
    <div class="header-box">
        <div class="portal-title">🏢 Enterprise Candidate Recruitment Portal</div>
        <div class="portal-subtitle">Application Status: <b>Ready for Submission</b></div>
    </div>
""",
    unsafe_allow_html=True,
)

steps_labels = [
    "1. Resume Autofill",
    "2. Personal Info",
    "3. Professional Experience",
    "4. Education & Qualifications",
    "5. Compliance & Review",
]
total_steps = len(steps_labels)
current_pct = int((st.session_state.current_step / total_steps) * 100)
st.progress(
    current_pct,
    text=(
        f"Progress: Step {st.session_state.current_step} of {total_steps}"
        f" ({steps_labels[st.session_state.current_step - 1]})"
    ),
)
st.write("")

# Sidebar Navigation & Export
with st.sidebar:
  st.markdown("### 🗂️ Navigation Tracker")
  for idx, label in enumerate(steps_labels, 1):
    status_icon = (
        "✅"
        if idx < st.session_state.current_step
        else ("👉" if idx == st.session_state.current_step else "⚪")
    )
    st.write(f"{status_icon} {label}")

  st.divider()
  st.markdown("### 📊 Admin Records")
  df_applicants = load_all_applicants()
  st.metric("Total Submitted Candidates", len(df_applicants))
  if not df_applicants.empty:
    csv_bytes = df_applicants.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download Candidates CSV",
        data=csv_bytes,
        file_name="enterprise_applicants.csv",
        mime="text/csv",
        use_container_width=True,
    )

# =====================================================================
# STEP 1: RESUME AUTOFILL
# =====================================================================
if st.session_state.current_step == 1:
  st.markdown(
      '<span class="section-badge">STEP 1 OF 5</span>', unsafe_allow_html=True
  )
  st.subheader("📄 Resume Upload & Smart Autofill")
  st.write(
      "Upload your CV (PDF or TXT) to automatically parse your information."
  )

  uploaded_file = st.file_uploader(
      "Upload CV / Resume (Optional)", type=["pdf", "txt"]
  )
  if uploaded_file:
    with st.spinner("Extracting profile details..."):
      parsed_vals = parse_resume(uploaded_file)
      st.session_state.form_data["resume_uploaded"] = True
      if parsed_vals:
        st.success("Information detected and staged for form fields!")
        for k, v in parsed_vals.items():
          st.session_state.form_data[k] = v
        with st.expander("🔍 View Extracted Entities", expanded=True):
          st.json(parsed_vals)

  st.divider()
  _, c2 = st.columns([4, 1])
  with c2:
    if st.button("Proceed to Personal Info ➡️", type="primary"):
      go_to_step(2)
      st.rerun()

# =====================================================================
# STEP 2: PERSONAL DETAILS & AGE SYNC
# =====================================================================
elif st.session_state.current_step == 2:
  st.markdown(
      '<span class="section-badge">STEP 2 OF 5</span>', unsafe_allow_html=True
  )
  st.subheader("👤 Personal Details & Demographics")

  col1, col2 = st.columns(2)
  with col1:
    st.session_state.form_data["full_name"] = st.text_input(
        "Full Legal Name *", value=st.session_state.form_data["full_name"]
    )
    st.session_state.form_data["email"] = st.text_input(
        "Email Address *", value=st.session_state.form_data["email"]
    )
    st.session_state.form_data["phone"] = st.text_input(
        "Contact Number *", value=st.session_state.form_data["phone"]
    )

  with col2:
    gender_list = ["Male", "Female", "Non-Binary", "Prefer not to say", "Other"]
    current_gender = st.session_state.form_data.get("gender", "Male")
    gender_idx = (
        gender_list.index(current_gender) if current_gender in gender_list else 0
    )
    st.session_state.form_data["gender"] = st.selectbox(
        "Gender Identity", gender_list, index=gender_idx
    )

    country_list = [
        "India",
        "United States",
        "United Kingdom",
        "Canada",
        "Germany",
        "Singapore",
    ]
    current_country = st.session_state.form_data.get("country", "India")
    country_idx = (
        country_list.index(current_country)
        if current_country in country_list
        else 0
    )
    st.session_state.form_data["country"] = st.selectbox(
        "Country / Nationality", country_list, index=country_idx
    )

    st.session_state.form_data["current_city"] = st.text_input(
        "Current City of Residence *",
        value=st.session_state.form_data["current_city"],
    )

  st.write("---")
  st.markdown("#### Date of Birth & Live Age Verification")
  st.session_state.form_data["dob"] = st.date_input(
      "Date of Birth", value=st.session_state.form_data["dob"]
  )

  col_age1, col_age2 = st.columns([1, 2])
  with col_age1:
    st.number_input(
        "Enter your age:",
        min_value=0,
        max_value=100,
        key="age_number",
        on_change=update_from_number,
    )

  with col_age2:
    st.slider(
        "Age (Slider View):",
        min_value=0,
        max_value=100,
        key="age_slider",
        on_change=update_from_slider,
    )

  st.divider()
  nav_prev, nav_next = st.columns([1, 1])
  with nav_prev:
    if st.button("⬅️ Back to Upload"):
      go_to_step(1)
      st.rerun()
  with nav_next:
    if st.button("Save & Continue ➡️", type="primary"):
      if (
          not st.session_state.form_data["full_name"]
          or not st.session_state.form_data["email"]
      ):
        st.error(
            "Please ensure Full Name and Email Address are both provided."
        )
      else:
        go_to_step(3)
        st.rerun()

# =====================================================================
# STEP 3: PROFESSIONAL EXPERIENCE & CTC (UNIFIED SLIDERS)
# =====================================================================
elif st.session_state.current_step == 3:
  st.markdown(
      '<span class="section-badge">STEP 3 OF 5</span>', unsafe_allow_html=True
  )
  st.subheader("💼 Professional Experience & Compensation")

  col1, col2 = st.columns(2)
  with col1:
    roles_list = [
        "Backend Engineer (FastAPI / Python)",
        "Data Scientist / AI Specialist",
        "Data Analyst / Business Intelligence",
        "DevOps / Cloud Architect",
        "Full Stack Software Developer",
    ]
    cur_role = st.session_state.form_data.get("primary_role", roles_list[0])
    role_idx = roles_list.index(cur_role) if cur_role in roles_list else 0
    st.session_state.form_data["primary_role"] = st.selectbox(
        "Target Designation *", roles_list, index=role_idx
    )

    st.session_state.form_data["current_company"] = st.text_input(
        "Current Organization / Employer",
        value=st.session_state.form_data["current_company"],
    )
    st.session_state.form_data["experience_years"] = st.slider(
        "Total Years of Relevant Experience",
        0,
        35,
        st.session_state.form_data["experience_years"],
    )

  with col2:
    pref_list = ["Hybrid", "Remote", "On-Site"]
    cur_pref = st.session_state.form_data.get("work_preference", "Hybrid")
    pref_idx = pref_list.index(cur_pref) if cur_pref in pref_list else 0
    st.session_state.form_data["work_preference"] = st.radio(
        "Preferred Working Model", pref_list, horizontal=True, index=pref_idx
    )

    cur_c_ctc = st.session_state.form_data.get("current_ctc")
    val_c_ctc = cur_c_ctc if cur_c_ctc in CTC_OPTIONS else "6-12 LPA"
    st.session_state.form_data["current_ctc"] = st.select_slider(
        "Current CTC Bracket",
        options=CTC_OPTIONS,
        value=val_c_ctc,
    )

    cur_e_ctc = st.session_state.form_data.get("expected_ctc")
    val_e_ctc = cur_e_ctc if cur_e_ctc in CTC_OPTIONS else "12-20 LPA"
    st.session_state.form_data["expected_ctc"] = st.select_slider(
        "Expected Compensation Bracket",
        options=CTC_OPTIONS,
        value=val_e_ctc,
    )

    notice_list = [
        "Immediate / Serving Notice",
        "15 Days",
        "30 Days",
        "60 Days",
        "90 Days",
    ]
    cur_notice = st.session_state.form_data.get("notice_period", "30 Days")
    notice_idx = (
        notice_list.index(cur_notice) if cur_notice in notice_list else 2
    )
    st.session_state.form_data["notice_period"] = st.selectbox(
        "Official Notice Period", notice_list, index=notice_idx
    )

  st.session_state.form_data["skills"] = st.multiselect(
      "Validated Technical & Core Skillsets:",
      options=[
          "Python",
          "FastAPI",
          "SQL",
          "Streamlit",
          "Docker",
          "Kubernetes",
          "AWS",
          "Machine Learning",
          "Pandas",
          "PyTorch",
          "Git",
          "Power BI",
      ],
      default=st.session_state.form_data["skills"],
  )

  st.divider()
  nav_prev, nav_next = st.columns([1, 1])
  with nav_prev:
    if st.button("⬅️ Back to Personal Info"):
      go_to_step(2)
      st.rerun()
  with nav_next:
    if st.button("Save & Proceed to Education ➡️", type="primary"):
      go_to_step(4)
      st.rerun()

# =====================================================================
# STEP 4: ACADEMIC CREDENTIALS
# =====================================================================
elif st.session_state.current_step == 4:
  st.markdown(
      '<span class="section-badge">STEP 4 OF 5</span>', unsafe_allow_html=True
  )
  st.subheader("🎓 Academic Credentials & Portfolios")

  col1, col2 = st.columns(2)
  with col1:
    edu_list = [
        "B.Tech / B.E.",
        "B.Sc / BCA",
        "M.Tech / M.E.",
        "MCA",
        "MBA",
        "Ph.D.",
    ]
    cur_edu = st.session_state.form_data.get("highest_education", edu_list[0])
    edu_idx = edu_list.index(cur_edu) if cur_edu in edu_list else 0
    st.session_state.form_data["highest_education"] = st.selectbox(
        "Highest Qualification Earned *", edu_list, index=edu_idx
    )

    st.session_state.form_data["college_name"] = st.text_input(
        "University / Institute Name *",
        value=st.session_state.form_data["college_name"],
    )
    st.session_state.form_data["passing_year"] = st.number_input(
        "Year of Graduation",
        min_value=1980,
        max_value=2030,
        step=1,
        value=st.session_state.form_data["passing_year"],
    )

  with col2:
    st.session_state.form_data["linkedin_url"] = st.text_input(
        "LinkedIn Profile URL",
        value=st.session_state.form_data["linkedin_url"],
        placeholder="https://linkedin.com/in/username",
    )
    st.session_state.form_data["portfolio_url"] = st.text_input(
        "GitHub / Portfolio / Personal Site",
        value=st.session_state.form_data["portfolio_url"],
        placeholder="https://github.com/username",
    )

  st.divider()
  nav_prev, nav_next = st.columns([1, 1])
  with nav_prev:
    if st.button("⬅️ Back to Experience"):
      go_to_step(3)
      st.rerun()
  with nav_next:
    if st.button("Save & Proceed to Compliance ➡️", type="primary"):
      if not st.session_state.form_data["college_name"]:
        st.error("Please specify your University or Institute Name.")
      else:
        go_to_step(5)
        st.rerun()

# =====================================================================
# STEP 5: COMPLIANCE & COMMIT TO DATABASE
# =====================================================================
elif st.session_state.current_step == 5:
  st.markdown(
      '<span class="section-badge">STEP 5 OF 5</span>', unsafe_allow_html=True
  )
  st.subheader("⚖️ Compliance, Review & Final Submission")

  with st.expander("📋 Review Your Candidate Summary Snapshot", expanded=True):
    r1, r2, r3 = st.columns(3)
    r1.metric("Applicant", st.session_state.form_data["full_name"])
    r2.metric("Target Role", st.session_state.form_data["primary_role"])
    r3.metric(
        "Experience",
        f"{st.session_state.form_data['experience_years']} Years",
    )

    r4, r5, r6 = st.columns(3)
    r4.metric("Age", f"{st.session_state.age_number} yrs")
    r5.metric("Work Mode", st.session_state.form_data["work_preference"])
    r6.metric("Notice Period", st.session_state.form_data["notice_period"])

  st.markdown("#### Mandatory Enterprise Declarations")
  st.session_state.form_data["bg_consent"] = st.checkbox(
      "I authorize the company to conduct standard third-party background and credential checks *",
      value=st.session_state.form_data["bg_consent"],
  )
  st.session_state.form_data["nc_ack"] = st.checkbox(
      "I confirm I am not bound by any enforceable non-compete agreements with current/past employers *",
      value=st.session_state.form_data["nc_ack"],
  )
  st.session_state.form_data["dp_consent"] = st.checkbox(
      "I consent to the processing and retention of my application data in compliance with enterprise data security guidelines *",
      value=st.session_state.form_data["dp_consent"],
  )
  st.session_state.form_data["declaration"] = st.checkbox(
      "I hereby declare that all information declared across this multi-page submission is accurate and true to my knowledge *",
      value=st.session_state.form_data["declaration"],
  )

  st.divider()
  nav_prev, nav_next = st.columns([1, 1])
  with nav_prev:
    if st.button("⬅️ Back to Education"):
      go_to_step(4)
      st.rerun()

  with nav_next:
    if st.button(
        "🚀 Submit Application to Database",
        type="primary",
        use_container_width=True,
    ):
      if not (
          st.session_state.form_data["bg_consent"]
          and st.session_state.form_data["nc_ack"]
          and st.session_state.form_data["dp_consent"]
          and st.session_state.form_data["declaration"]
      ):
        st.error("⚠️ You must accept all mandatory declarations before submitting.")
      else:
        # Commit age_number value into form payload
        st.session_state.form_data["age"] = st.session_state.age_number

        # Save to database (unique ID handled per insert)
        save_final_applicant(st.session_state.form_data)

        st.balloons()
        st.success("🎉 Application submitted and stored permanently in database!")

        with st.expander("🔍 Committed Applicant Record (JSON)", expanded=True):
          st.json(st.session_state.form_data)

# Bottom Admin Viewer
df_all = load_all_applicants()
if not df_all.empty:
  st.divider()
  with st.expander("📂 HR Admin: View All Applications Database", expanded=False):
    st.dataframe(df_all, use_container_width=True)
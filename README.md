# 🏢 Enterprise Candidate Recruitment Portal

An interactive, multi-step talent acquisition and onboarding portal built with **Streamlit**, featuring automated resume entity extraction, dynamic demographic state synchronization, and persistent local storage powered by **SQLite**.

---

## 🌟 Key Highlights

- **Multi-Step Wizard Architecture**: Seamless 5-stage sequential application flow managed dynamically using Streamlit's `session_state` to prevent data loss across page transitions.
- **Smart CV Autofill**: Automated resume parsing engine leveraging `pypdf` to extract candidate legal names, email addresses, contact numbers, LinkedIn URLs, and matching technical competencies.
- **Bidirectional Demographic Synchronization**: Coordinated live input state connecting numeric input and slider widgets using reactive callbacks.
- **Robust Data Persistence**: Complete transactional storage in a local SQLite database (`applicant_portal.db`) utilizing `INSERT OR REPLACE` and unique UUIDs to prevent constraint collisions.
- **HR Administrative Toolkit**: Dedicated data viewer and instant single-click CSV export directly from the sidebar.

---

## 🧭 Multi-Stage Application Workflow

| Step | Module | Key Features |
| :--- | :--- | :--- |
| **01** | **Resume Autofill** | CV upload (PDF/TXT) with instant automated entity parsing. |
| **02** | **Personal Details** | Identity info, demographics, and synchronized age controls. |
| **03** | **Professional Experience** | Target roles, CTC brackets, notice periods, and skill sets. |
| **04** | **Academic Credentials** | Qualification history, institutions, and digital portfolio links. |
| **05** | **Compliance & Review** | Candidate profile snapshot, mandatory legal declarations, and database submission. |

---

## 🛠️ Tech Stack

- **Frontend & App Framework**: [Streamlit](https://streamlit.io/)
- **Document Processing**: [pypdf](https://pypi.org/project/pypdf/)
- **Data Persistence**: SQLite3
- **Data Manipulation & Export**: Pandas

---

## 🚀 Getting Started Locally

### 1. Clone the Repository
```bash
git clone [https://github.com/ShashwatMisra008/Streamlit_app---Candidate-Portal.git](https://github.com/ShashwatMisra008/Streamlit_app---Candidate-Portal.git)
cd Streamlit_app---Candidate-Portal

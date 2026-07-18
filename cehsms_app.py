# -*- coding: utf-8 -*-
"""
نظام تتبع الحالات الكيميائية والحرجة (HAZMAT Tracker)
Chemical Emergency & Hospital Safety Management System (CEHSMS)
نسخة Python / Streamlit
"""

import json
import os
import re
from datetime import datetime

import pandas as pd
import streamlit as st

# --------------------------------------------------------------------------
# إعدادات عامة
# --------------------------------------------------------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
SDS_PATH = os.path.join(APP_DIR, "sds_database.json")
ENTRIES_PATH = os.path.join(DATA_DIR, "entries.csv")

st.set_page_config(
    page_title="نظام تتبع الحالات الكيميائية والحرجة",
    page_icon="⚠️",
    layout="wide",
)

# --------------------------------------------------------------------------
# RTL + تنسيق عام (CSS)
# --------------------------------------------------------------------------
st.markdown(
    """
    <style>
    html, body, [class*="css"]  { direction: rtl; text-align: right; }
    .stApp { background-color: #ffffff; }
    section[data-testid="stSidebar"] { direction: rtl; text-align: right; }
    .decon-alert{
        background: rgba(194,54,22,.1);
        border: 2px solid #c23616;
        color: #c23616;
        font-weight:700;
        border-radius:6px;
        padding:10px 14px;
        margin: 8px 0;
    }
    .decon-tag{
        display:inline-block;
        background:#c23616;
        color:#fff;
        font-weight:700;
        font-size:.75rem;
        padding:3px 9px;
        border-radius:4px;
        margin-bottom:6px;
    }
    .locked-note{
        background: rgba(184,121,10,.1);
        border:1px solid #b8790a;
        border-radius:6px;
        padding:10px 14px;
        font-size:.9rem;
    }
    .sev-badge{
        display:inline-block;
        padding:3px 12px;
        border-radius:4px;
        font-size:.8rem;
        font-weight:700;
        color:#fff;
    }
    .datetime-tag{
        display:inline-block;
        background:#eef1f4;
        color:#334;
        font-size:.78rem;
        padding:3px 10px;
        border-radius:4px;
        margin-inline-start:6px;
    }
    .sev-0{ background:#2e8b57; }
    .sev-1{ background:#c9a227; }
    .sev-2{ background:#b8790a; }
    .sev-3{ background:#c23616; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# بيانات المستخدمين (Demo only — client is not the source of truth in prod)
# يُفضّل نقلها إلى st.secrets عند النشر الفعلي على Streamlit Cloud / GitHub
# --------------------------------------------------------------------------
USERS = {
    "owner": {"pass": "Owner#2025", "role": "مالك النظام", "is_owner": True},
    "admin": {"pass": "1234", "role": "قائد الفريق", "is_owner": False},
}

LOCATION_TEXT = {
    "emergency": "قسم الطوارئ",
    "icu": "العناية المركزة",
    "ward": "قسم داخلي",
    "field": "موقع الحادث (ميداني)",
    "other": "أخرى",
}
ROUTE_TEXT = {
    "skin": "عن طريق الجلد",
    "inhalation": "استنشاق",
    "ingestion": "بلع",
    "eye": "العين",
    "injection": "حقن / اختراق",
    "unknown": "غير معروف",
}
SEVERITY_TEXT = {
    "mild": "بسيطة",
    "moderate": "متوسطة",
    "severe": "شديدة",
    "critical": "حرجة",
}
DECON_TEXT = {"yes": "مطلوبة", "no": "غير مطلوبة", "unknown": "غير محدد"}
HAZMAT_TEXT = {"yes": "مطلوب", "no": "غير مطلوب", "unknown": "غير محدد"}


# --------------------------------------------------------------------------
# تحميل قاعدة بيانات SDS
# --------------------------------------------------------------------------
@st.cache_data
def load_sds_database():
    with open(SDS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_entries():
    cols = [
        "time", "hospital_name", "patient", "patient_gender", "patient_age",
        "incident_date", "incident_time",
        "patient_profession", "location", "casualty_count", "material",
        "route", "severity", "sds", "first_aid", "needs_decon",
        "needs_hazmat_team", "notes", "responder", "entry_datetime",
    ]
    if os.path.exists(ENTRIES_PATH):
        try:
            return pd.read_csv(ENTRIES_PATH)
        except Exception:
            return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)


def save_entries(df: pd.DataFrame):
    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(ENTRIES_PATH, index=False)


# --------------------------------------------------------------------------
# تسجيل الدخول
# --------------------------------------------------------------------------
def login_screen():
    st.title("⚠️ نظام تتبع الحالات الكيميائية والحرجة")
    st.caption("Chemical Emergency & Hospital Safety Management System")
    with st.form("login_form"):
        u = st.text_input("اسم المستخدم")
        p = st.text_input("كلمة المرور", type="password")
        submitted = st.form_submit_button("تسجيل الدخول")
    if submitted:
        record = USERS.get(u)
        if record and record["pass"] == p:
            st.session_state.logged_in = True
            st.session_state.username = u
            st.session_state.role = record["role"]
            st.session_state.is_owner = record["is_owner"]
            st.rerun()
        else:
            st.error("اسم المستخدم أو كلمة المرور غير صحيحة.")


# --------------------------------------------------------------------------
# مساعدات لاكتشاف مادة تحتاج إزالة تلوث إلزامية
# --------------------------------------------------------------------------
def needs_mandatory_decon(item: dict) -> bool:
    return bool(item.get("skinDeconMandatory"))


# --------------------------------------------------------------------------
# صفحة: بيانات الحالة (إدخال حالة جديدة)
# --------------------------------------------------------------------------
def page_new_case(sds_db):
    st.header("🧾 بيانات الحالة")

    material_names = ["-- اختر مادة (اختياري) --"] + [m["name"] for m in sds_db]

    with st.form("new_case_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            hospital_name = st.text_input("اسم المستشفى")
            incident_date = st.date_input("📅 تاريخ الحادث", value=datetime.now().date())
            incident_time = st.time_input("⏰ وقت الحادث", value=datetime.now().time())
            patient = st.text_input("اسم المريض / الحالة")
            patient_gender = st.selectbox("النوع", ["ذكر", "أنثى"])
            patient_age = st.number_input("العمر", min_value=0, max_value=120, step=1)
            patient_profession = st.text_input("المهنة")
        with c2:
            location = st.selectbox(
                "مكان الإصابة", list(LOCATION_TEXT.keys()),
                format_func=lambda k: LOCATION_TEXT[k],
            )
            casualty_count = st.number_input("عدد المصابين", min_value=1, step=1, value=1)
            material_sel = st.selectbox("المادة المشتبه بها", material_names)
            route = st.selectbox(
                "طريقة وصول المادة", list(ROUTE_TEXT.keys()),
                format_func=lambda k: ROUTE_TEXT[k],
            )
            severity = st.selectbox(
                "درجة الخطورة", list(SEVERITY_TEXT.keys()),
                format_func=lambda k: SEVERITY_TEXT[k],
            )

        notes = st.text_area("الوصف / الأعراض / الإجراء المتخذ")

        c3, c4 = st.columns(2)
        with c3:
            needs_decon = st.selectbox(
                "الحاجة لإزالة التلوث (Decontamination)",
                list(DECON_TEXT.keys()), format_func=lambda k: DECON_TEXT[k],
            )
        with c4:
            needs_hazmat_team = st.selectbox(
                "الحاجة لتفعيل فريق HAZMAT",
                list(HAZMAT_TEXT.keys()), format_func=lambda k: HAZMAT_TEXT[k],
            )

        submitted = st.form_submit_button("➕ تسجيل الحالة")

    # عرض بيانات SDS للمادة المختارة (خارج الفورم حتى تتحدث فورًا)
    if material_sel != material_names[0]:
        item = next((m for m in sds_db if m["name"] == material_sel), None)
        if item:
            st.subheader(f"⚕ الإسعافات الأولية — {item['name']}")
            if needs_mandatory_decon(item):
                st.markdown(
                    '<div class="decon-alert">🛑 إزالة التلوث إلزامية: طريقة وصول '
                    'المادة عن طريق الجلد — يجب غسل جيد بالماء وخلع الملابس الملوثة فورًا</div>',
                    unsafe_allow_html=True,
                )
            st.write(item["firstAid"])
            st.caption(
                f"NFPA — الصحة: {item['nfpa']['h']} · الاشتعال: {item['nfpa']['f']} "
                f"· التفاعلية: {item['nfpa']['r']} · مهمات الوقاية: {item['ppe']}"
            )

    if submitted:
        item = next((m for m in sds_db if m["name"] == material_sel), None)
        first_aid = item["firstAid"] if item else ""
        sds_ref = item["cas"] if item else "-"

        entries = load_entries()
        new_row = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "hospital_name": hospital_name,
            "incident_date": str(incident_date),
            "incident_time": incident_time.strftime("%H:%M"),
            "patient": patient,
            "patient_gender": patient_gender,
            "patient_age": patient_age,
            "patient_profession": patient_profession,
            "location": location,
            "casualty_count": casualty_count,
            "material": material_sel if item else "غير محدد",
            "route": route,
            "severity": severity,
            "sds": sds_ref,
            "first_aid": first_aid,
            "needs_decon": needs_decon,
            "needs_hazmat_team": needs_hazmat_team,
            "notes": notes,
            "responder": st.session_state.username,
            "entry_datetime": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

        # تحقق من الحقول الإلزامية قبل الحفظ
        missing = []
        if not hospital_name.strip():
            missing.append("اسم المستشفى")
        if not patient.strip():
            missing.append("اسم المريض")
        if material_sel == material_names[0]:
            missing.append("اسم المادة")

        if missing:
            st.error("⚠ برجاء تعبئة الحقول الإلزامية التالية: " + "، ".join(missing))
        else:
            entries = pd.concat([entries, pd.DataFrame([new_row])], ignore_index=True)
            save_entries(entries)
            st.success("تم تسجيل الحالة بنجاح ✅")


# --------------------------------------------------------------------------
# صفحة: متابعة الحالة (سجل الحالات)
# --------------------------------------------------------------------------
def page_case_log():
    st.header("📋 متابعة الحالة — سجل الحالات المسجّلة")
    entries = load_entries()
    is_owner = st.session_state.get("is_owner", False)

    if entries.empty:
        st.info("لا توجد حالات مسجّلة بعد.")
        return

    for i, e in entries.iloc[::-1].iterrows():
        sev = e.get("severity", "mild")
        sev_class = {"mild": "sev-0", "moderate": "sev-1",
                     "severe": "sev-2", "critical": "sev-3"}.get(sev, "sev-0")
        with st.container(border=True):
            st.markdown(
                f'<span class="sev-badge {sev_class}">{SEVERITY_TEXT.get(sev, sev)}</span> '
                f'&nbsp; <b>{e.get("time","")}</b> — المستشفى: {e.get("hospital_name","")} '
                f'<span class="datetime-tag">📅 {e.get("incident_date","")} '
                f'⏰ {e.get("incident_time","")}</span>',
                unsafe_allow_html=True,
            )
            if is_owner:
                st.write(
                    f"**{e.get('patient','')}** — {e.get('patient_gender','')} — "
                    f"العمر: {e.get('patient_age','')} — المهنة: {e.get('patient_profession','')}"
                )
            else:
                st.markdown(
                    f"**حالة رقم {i+1}** — 🔒 بيانات المريض الشخصية محجوبة "
                    "(متاحة لمالك النظام فقط)"
                )
            st.write(
                f"مكان الإصابة: {LOCATION_TEXT.get(e.get('location',''), e.get('location',''))}"
                f" — عدد المصابين: {e.get('casualty_count','')}"
            )
            st.write(
                f"المادة: {e.get('material','')} — طريقة الوصول: "
                f"{ROUTE_TEXT.get(e.get('route',''), e.get('route',''))}"
            )
            st.write(f"إزالة التلوث: {DECON_TEXT.get(e.get('needs_decon',''), '')} "
                      f"— فريق HAZMAT: {HAZMAT_TEXT.get(e.get('needs_hazmat_team',''), '')}")
            if is_owner:
                if str(e.get("notes", "")).strip() and str(e.get("notes")) != "nan":
                    st.write(f"ملاحظات: {e.get('notes')}")
                st.caption(f"المسجّل: {e.get('responder','')} — وقت التسجيل: {e.get('entry_datetime','')}")

    st.divider()
    if is_owner:
        st.subheader("تصدير البيانات")
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "⬇️ تحميل CSV", entries.to_csv(index=False).encode("utf-8-sig"),
                file_name="hazmat_report.csv", mime="text/csv",
            )
        with c2:
            st.download_button(
                "⬇️ تحميل JSON",
                entries.to_json(orient="records", force_ascii=False, indent=2).encode("utf-8"),
                file_name="hazmat_report.json", mime="application/json",
            )
    else:
        st.markdown(
            '<div class="locked-note">🔒 تصدير البيانات متاح لمالك النظام فقط، '
            'لأنها تحتوي على بيانات المرضى الحساسة.</div>',
            unsafe_allow_html=True,
        )


# --------------------------------------------------------------------------
# صفحة: لوحة التحكم (owner فقط)
# --------------------------------------------------------------------------
def page_dashboard():
    st.header("📊 لوحة التحكم")
    entries = load_entries()

    if entries.empty:
        st.info("لا توجد بيانات كافية لعرض لوحة التحكم بعد.")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("إجمالي الحالات", len(entries))
    c2.metric("تحتاج إزالة تلوث", int((entries["needs_decon"] == "yes").sum()))
    c3.metric("تحتاج فريق HAZMAT", int((entries["needs_hazmat_team"] == "yes").sum()))
    c4.metric("حالات حرجة", int((entries["severity"] == "critical").sum()))

    st.subheader("توزيع الحالات حسب درجة الخطورة")
    st.bar_chart(entries["severity"].value_counts())

    st.subheader("توزيع الحالات حسب مكان الإصابة")
    st.bar_chart(entries["location"].value_counts())

    st.subheader("أكثر المواد تكرارًا")
    st.bar_chart(entries["material"].value_counts().head(10))


# --------------------------------------------------------------------------
# صفحة: قاعدة بيانات SDS
# --------------------------------------------------------------------------
def page_sds_database(sds_db):
    st.header("🧪 قاعدة بيانات SDS")
    search = st.text_input("ابحث باسم المادة (مثال: كلور، ايثانول، ميثانول...)")

    filtered = sds_db
    if search.strip():
        s = search.strip()
        filtered = [
            m for m in sds_db
            if s in m["name"] or s in m.get("trade", "") or s in m.get("cas", "")
        ]

    st.caption(f"عدد المواد: {len(filtered)} من إجمالي {len(sds_db)}")

    names = [m["name"] for m in filtered]
    if not names:
        st.warning("لا توجد نتائج مطابقة.")
        return

    chosen = st.selectbox("اختر مادة لعرض التفاصيل", names)
    item = next(m for m in filtered if m["name"] == chosen)

    if needs_mandatory_decon(item):
        st.markdown('<div class="decon-tag">🛑 إزالة تلوث إلزامية</div>', unsafe_allow_html=True)

    st.subheader(item["name"])
    st.caption(f"{item.get('trade','')} — CAS: {item.get('cas','')}")

    c1, c2, c3 = st.columns(3)
    c1.metric("NFPA — الصحة", item["nfpa"]["h"])
    c2.metric("NFPA — الاشتعال", item["nfpa"]["f"])
    c3.metric("NFPA — التفاعلية", item["nfpa"]["r"])

    st.write(f"**الحالة الفيزيائية:** {item.get('state','-')}")
    st.write(f"**الاستخدامات:** {item.get('uses','-')}")
    st.write(f"**التخزين:** {item.get('storage','-')}")
    st.write(f"**التسرب/الانسكاب:** {item.get('spill','-')}")
    st.write(f"**التأثير على الصحة:** {item.get('health','-')}")

    if needs_mandatory_decon(item):
        st.markdown(
            '<div class="decon-alert">🛑 إزالة التلوث إلزامية: طريقة وصول المادة '
            'عن طريق الجلد — يجب غسل جيد بالماء وخلع الملابس الملوثة فورًا</div>',
            unsafe_allow_html=True,
        )

    st.write(f"**الإسعافات الأولية:** {item.get('firstAid','-')}")
    st.write(f"**مهمات الوقاية:** {item.get('ppe','-')}")


# --------------------------------------------------------------------------
# صفحة: لدغات الأفاعي والعقارب
# --------------------------------------------------------------------------
def page_bites():
    st.header("لدغات الأفاعي والعقارب — بروتوكولات الإسعاف والعلاج")
    tab_scorpion, tab_snake = st.tabs(["🦂 لدغة العقرب", "🐍 لدغة الثعبان"])

    with tab_scorpion:
        st.subheader("الإسعافات الأولية")
        st.markdown(
            """
1. طمأنة المصاب ومحاولة إبقائه هادئًا.
2. إزالة الذنب إن وُجد باستخدام جسم مسطح مثل الكارت، وليس جسمًا حادًا، مع مراعاة
   عدم استخدام ملقاط لأنه يتسبب في عصر مكان الإصابة وزيادة إفراز السم للدورة الدموية.
3. غسل مكان الإصابة بالماء والصابون مع إزالة الخواتم والساعة والحلي من الطرف
   المصاب لاحتمال تورّمه.
4. يمكن استخدام رباط شاش أعلى مكان الإصابة مع مراعاة أن يُربط بخفة بحيث يغلق
   الوريد فقط وليس الشريان.
5. استخدام ثلج ملفوف بقماش على مكان الإصابة لمدة 10 دقائق ثم إزالته لمدة 10
   دقائق أخرى مع التكرار.
6. عدم استخدام أي مسكنات إلا بعد استشارة طبيب.
7. تسجيل العلامات الحيوية للمصاب، خاصة النبض والتنفس وضغط الدم.
            """
        )

        st.subheader("تقييم حالة المصاب والتعامل العلاجي")
        scorpion_df = pd.DataFrame(
            [
                ["مستوى 0 — لا تأثير", "لا توجد أعراض أو علامات موضعية أو عامة", "لا يحتاج إلى علاج"],
                ["مستوى 1 — قليلة التأثير",
                 "علامات موضعية: ألم، تنميل، خدر مكان اللدغة، برودة أطراف، هبوط ضغط",
                 "1–2 أمبولة مصل بالعضل/تحت الجلد بعد اختبار الحساسية، تكرار بعد 1–2 ساعة عند عدم التحسن"],
                ["مستوى 2 — متوسط التأثير",
                 "أعراض المستوى 1 + تسرع/اختلال ضربات القلب + غثيان وقيء",
                 "5 أمبولات مخففة 1:10 بالتنقيط الوريدي على مدى 30 دقيقة"],
                ["مستوى 3 — شديدة التأثير",
                 "أعراض المستوى 2 + خلل عصبي-عضلي بأي مكان بالجسم",
                 "نفس بروتوكول المستوى 2 مع دخول القسم الداخلي بالمستشفى"],
            ],
            columns=["المستوى", "الأعراض السريرية", "التعامل العلاجي"],
        )
        st.table(scorpion_df)

        st.info(
            "ملحوظات: تُزاد الجرعة عند الإصابة بالرأس/الرقبة/الكتف أو تأخر العلاج "
            "(حتى 10 أمبولات) — يجب اختبار الحساسية الجلدية قبل إعطاء المصل — "
            "يُحفظ المذيب بحرارة 2–8°م."
        )
        st.caption("المصدر: البروتوكول العلاجي للتعامل مع حالات لدغ العقرب — "
                    "lms.ehc.gov.eg/lms/mod/book/view.php?id=559&chapterid=3403")

    with tab_snake:
        st.subheader("الإسعافات الأولية الفورية")
        st.markdown(
            """
- **طمأنة المصاب:** الحفاظ على الهدوء يقلل سرعة انتشار السم.
- **تثبيت الطرف المصاب:** وضعه أقل من مستوى القلب وتقليل حركته بجبيرة.
- **إزالة الأشياء الضاغطة:** الخواتم والساعات والأحذية الضيقة قبل حدوث التورم.
- **إزالة أي رباط ضاغط** رُبط سابقًا تدريجيًا وبحذر، دون ربط رباط جديد.
- **تحديد وقت اللدغة بدقة** لتقييم شدة التسمم.
- النقل الفوري لأقرب مستشفى مع متابعة العلامات الحيوية.
            """
        )

        st.subheader("الأعراض الإكلينيكية")
        c1, c2 = st.columns(2)
        c1.write("**موضعيًا:** آثار الأنياب، ألم، تورم، فقاعات نزفية، تموّت نسيجي")
        c2.write("**جهازيًا:** عامة، دموية، عصبية، قلبية-وعائية، بولية-تناسلية، عينية")

        st.subheader("الفحوصات المطلوبة")
        st.markdown(
            """
- صورة دم كاملة (C.B.C)
- زمن النزف وP.T وP.T.T وI.N.R وFDPDs (مهمة في لدغة الأفعى)
- وظائف الكلى (B.U.N والكرياتينين)
- غازات الدم الشرياني ABGs (حيوية في لدغة الكوبرا)
- إنزيمات الكبد والعضلات (كشف انحلال العضلات)
- رسم قلب كهربائي ومتابعة مستمرة
            """
        )

        st.subheader("العلاج")
        st.markdown(
            """
- تثبيت الطرف والاهتمام بمجرى الهواء والتنفس والدورة الدموية (ABC)
- مصل التيتانوس
- مراقبة المريض 24 ساعة على الأقل
- تسكين الألم بالباراسيتامول (وليس الأسبرين أو NSAIDs) أو ترامادول 50 مجم
            """
        )

        st.subheader("الإجراءات النوعية (مصل مضاد السم) حسب درجة التسمم")
        snake_df = pd.DataFrame(
            [
                ["لا يوجد تسمم (لدغة جافة)", "آثار أنياب دون رد فعل موضعي أو جهازي", "لا يوجد"],
                ["خفيفة", "تورم وألم موضعي دون رد فعل جهازي", "1–3 أمبولات وريديًا بتخفيف 1:10"],
                ["متوسطة", "تأثيرات موضعية واسعة أو جهازية خفيفة وتشوهات معملية خفيفة",
                 "3–5 أمبولات وريديًا بتخفيف 1:10"],
                ["شديدة", "تأثيرات موضعية وجهازية واسعة وتشوهات معملية واضحة، قد تصل لـ 20 أمبولة",
                 "5–10 أمبولات وريديًا بتخفيف 1:10"],
            ],
            columns=["الدرجة", "الملامح", "الجرعة"],
        )
        st.table(snake_df)
        st.caption("المصدر: وزارة الصحة والسكان المصرية — الإدارة المركزية للرعاية الحرجة والعاجلة")


# --------------------------------------------------------------------------
# التطبيق الرئيسي
# --------------------------------------------------------------------------
def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login_screen()
        return

    sds_db = load_sds_database()
    is_owner = st.session_state.get("is_owner", False)

    with st.sidebar:
        st.markdown(f"**{st.session_state.username}** ({st.session_state.role})"
                     + (" 👑" if is_owner else ""))
        pages = ["🧾 بيانات الحالة", "📋 متابعة الحالة"]
        if is_owner:
            pages.append("📊 لوحة التحكم")
        pages += ["🐍🦂 لدغات الأفاعي والعقارب", "🧪 قاعدة بيانات SDS"]
        choice = st.radio("التنقل", pages)

        st.divider()
        if st.button("🚪 تسجيل الخروج"):
            for k in ["logged_in", "username", "role", "is_owner"]:
                st.session_state.pop(k, None)
            st.rerun()

    if choice == "🧾 بيانات الحالة":
        page_new_case(sds_db)
    elif choice == "📋 متابعة الحالة":
        page_case_log()
    elif choice == "📊 لوحة التحكم":
        if is_owner:
            page_dashboard()
        else:
            st.error("لوحة التحكم متاحة لمالك النظام فقط.")
    elif choice == "🐍🦂 لدغات الأفاعي والعقارب":
        page_bites()
    elif choice == "🧪 قاعدة بيانات SDS":
        page_sds_database(sds_db)


if __name__ == "__main__":
    main()

# نظام تتبع الحالات الكيميائية والحرجة (HAZMAT Tracker) — نسخة Streamlit

نسخة Python من برنامج تتبع حالات التسمم والتعرض الكيميائي بالمستشفيات،
مبنية باستخدام [Streamlit](https://streamlit.io) وجاهزة للنشر مباشرة من GitHub.

## المميزات
- تسجيل حالات جديدة مع اختيار المادة الكيميائية من قاعدة بيانات SDS (296 مادة).
- تنبيه أحمر تلقائي لإزالة التلوث الإلزامية للمواد التي يدخل الجلد كمسار للتعرض.
- سجل متابعة الحالات، مع إخفاء البيانات الشخصية الحساسة عن غير المالك.
- لوحة تحكم إحصائية (لمالك النظام فقط).
- قسم منفصل لبروتوكولات لدغات العقرب والثعبان (تابين مستقلين).
- نظام دخول بصلاحيتين: **مالك النظام** و**مستخدم عادي**.

## بيانات الدخول التجريبية
| المستخدم | كلمة المرور | الصلاحية |
|---|---|---|
| `owner` | `Owner#2025` | مالك النظام (كل الصلاحيات) |
| `admin` | `1234` | مستخدم عادي (بدون لوحة تحكم أو بيانات حساسة) |

⚠️ **مهم:** هذه بيانات دخول تجريبية مكتوبة داخل `app.py`. قبل أي استخدام حقيقي،
انقلها إلى [`st.secrets`](https://docs.streamlit.io/develop/concepts/connections/secrets-management)
حتى لا تظهر في كود GitHub العلني.

## التشغيل محليًا
```bash
pip install -r requirements.txt
streamlit run app.py
```

## النشر على GitHub + Streamlit Community Cloud
1. أنشئ مستودع (repository) جديد على GitHub وارفع محتويات هذا المجلد إليه:
   ```bash
   git init
   git add .
   git commit -m "Initial commit - HAZMAT Tracker (Streamlit)"
   git branch -M main
   git remote add origin https://github.com/<username>/<repo-name>.git
   git push -u origin main
   ```
2. ادخل إلى [share.streamlit.io](https://share.streamlit.io) وسجّل الدخول بحساب GitHub.
3. اضغط **New app**، واختر المستودع والفرع (`main`) وملف التشغيل `app.py`.
4. (اختياري لكن موصى به) من إعدادات التطبيق → **Secrets**، أضف بيانات الدخول بدلًا
   من تركها في الكود:
   ```toml
   [users.owner]
   pass = "Owner#2025"
   role = "مالك النظام"
   is_owner = true

   [users.admin]
   pass = "1234"
   role = "قائد الفريق"
   is_owner = false
   ```
   ثم عدّل `USERS` في `app.py` لتُقرأ من `st.secrets["users"]` بدلًا من القاموس الثابت.
5. اضغط **Deploy** — سيصبح التطبيق متاحًا برابط عام خلال دقائق.

## هيكل المشروع
```
├── app.py                     # التطبيق الرئيسي
├── requirements.txt           # الاعتماديات
├── data/
│   └── sds_database.json      # قاعدة بيانات SDS (296 مادة)
├── .streamlit/
│   └── config.toml            # الثيم (خلفية بيضاء)
└── README.md
```

## ملاحظة عن تخزين البيانات
حالات المرضى تُحفظ في `data/entries.csv` عبر pandas. على Streamlit Community
Cloud التخزين **غير دائم** (يُعاد ضبطه عند إعادة تشغيل/نشر التطبيق). لتخزين
دائم وحقيقي للحالات، يُنصح بربط التطبيق بقاعدة بيانات خارجية (مثل
PostgreSQL أو Google Sheets أو Supabase) بدلًا من ملف CSV محلي.

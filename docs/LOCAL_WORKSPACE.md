# Miyaar local workspace / مساحة معيار المحلية

This is the real single-person application, not the public fictional demo. It
uses the existing `local-owner` identity (workspace owner, not platform admin),
SQLite, dataset processing, review/approval gates and durable reports. There is
no shared/default password and no new account, key or authentication system.
Hosted managed identity, Supabase integration and existing data are unchanged.

هذه هي مساحة التطبيق الفعلية لشخص واحد، وليست العرض التجريبي العام. تستخدم
الهوية المحلية الحالية `local-owner` وقاعدة SQLite، مع معالجة البيانات ومراجعة
النتائج والموافقة عليها. لا توجد كلمة مرور افتراضية مشتركة ولا حساب أو مفتاح
جديد. تبقى حماية النسخة المنشورة وبيانات Supabase كما هي.

## Start / التشغيل

Prerequisites: Python 3.11 or 3.12, Node.js 22 and npm on Linux, macOS or
Windows. Use the repository's existing Python environment and install its
locked requirements if needed. Build the interface once:

المتطلبات: Python 3.11 أو 3.12 وNode.js 22 وnpm على Linux أو macOS أو
Windows. استخدم بيئة Python الخاصة بالمستودع وثبّت متطلباته المقفلة عند الحاجة.

```sh
python -m pip install --require-hashes -r requirements.txt
npm --prefix frontend ci
npm --prefix frontend run build
python scripts/local_workspace.py start
```

Open http://127.0.0.1:8000. The existing interface enters local mode without a
sign-in form. Stop with Ctrl+C and run the same command to resume. The default
durable directory is `.miyaar/workspace` under your home directory, separate
from repository data and any hosted database. Choose another location with
`--workspace /absolute/path/to/workspace` and reuse it on every command.

افتح العنوان أعلاه؛ تظهر الواجهة مباشرة دون نموذج تسجيل دخول. أوقف التشغيل
بـ Ctrl+C ثم استخدم الأمر نفسه لاستكمال العمل. تُحفظ البيانات داخل
`.miyaar/workspace` في مجلد المستخدم، منفصلة عن بيانات المستودع والسحابة.
يمكن تغيير الموقع باستخدام `--workspace` مع إعادة استخدام المسار نفسه.

Start in a clean shell without hosted database, Supabase, JWT, production or
cloud-model settings. The launcher refuses conflicts rather than clearing
`REQUIRE_AUTH`, changing stored settings or falling back to unauthenticated
hosted access. It does not read `.env` files, install models, download weights,
create credentials or start a worker. Existing browser-driven analysis runs
remain supported. It does not configure scheduled/background connectors.

ابدأ من جلسة أوامر نظيفة لا تحمل إعدادات قاعدة بيانات سحابية أو Supabase أو
JWT أو production أو مفاتيح نماذج سحابية. يرفض المشغّل التعارض بدل تعطيل
الحماية. لا يحمّل نماذج ولا ينشئ بيانات دخول ولا يشغّل عاملًا خلفيًا؛ يستمر
مسار التحليل الذي تقوده الواجهة كالمعتاد.

## AI is separate / الذكاء الاصطناعي مستقل

Dataset calculations and the existing clearly labelled deterministic report
work without an LLM. This is not evidence of model-generated analysis. For AI,
use an already-installed local Ollama model and explicitly select it with
`OLLAMA_MODEL`; the endpoint must be loopback HTTP. No cloud provider fallback
is permitted in this local profile. The launcher does not start or install
Ollama. If a local model is unavailable, the existing gateway reports its
unavailability; do not claim a successful model response.

تعمل الحسابات والتقرير الحتمي المسمّى بوضوح دون نموذج لغوي؛ هذا ليس توليدًا
بالذكاء الاصطناعي. لتفعيل النموذج، اختر نموذج Ollama محليًا مثبتًا مسبقًا
باستخدام `OLLAMA_MODEL`. لا يُسمح ببديل سحابي في هذا الوضع، ولا يثبّت المشغّل
Ollama أو يشغّله. تعذّر النموذج لا يعني نجاح توليد نص.

## Back up and restore / النسخ الاحتياطي والاستعادة

Stop the app before recovery. Backups contain private data; keep them out of
Git and do not upload them publicly. Backup uses the existing database export;
local-profile memory lives in that database too. This covers datasets, runs,
sessions, memory and stored report/vault evidence. It does not bundle model
weights, external knowledge folders or external connector credentials.

```sh
python scripts/local_workspace.py backup --out /private/path/miyaar-backup.json
python scripts/local_workspace.py restore --from-backup /private/path/miyaar-backup.json --workspace /private/path/miyaar-recovered
python scripts/local_workspace.py start --workspace /private/path/miyaar-recovered
```

The backup file must be new. Restore only accepts a new empty workspace; it
never replaces the original. Restore only backups you trust. Keep the original
until the recovered workspace has been checked.

أوقف التطبيق قبل الاستعادة. النسخة الاحتياطية تحتوي بيانات خاصة، فلا تضعها
في Git أو تنشرها. تشمل البيانات والجلسات والذاكرة والتقارير المخزّنة، ولا
تشمل أوزان النماذج أو مجلدات المعرفة الخارجية. يجب أن يكون ملف النسخة جديدًا،
وتتم الاستعادة فقط إلى مجلد جديد فارغ. احتفظ بالأصل حتى التحقق من الاستعادة،
ولا تستعد إلا نسخة موثوقة.

## Security boundary / حدود الأمان

This mode trusts the operating-system user and other local processes. It is
not appropriate for a shared/untrusted computer or multiple independent users.
The listener binds only to 127.0.0.1 and ignores proxy-header trust. The app also
rejects non-loopback peers/hosts, cross-origin and cross-site requests, forwarded
headers and known cloud-hosting configuration. No LAN, public deployment,
reverse proxy, tunnel or container port publication is supported. A local proxy
that removes every trace of forwarding cannot be distinguished from another
trusted local process; never put this mode behind one. Use managed identity for
network access. Authentication throttling does not apply because there is no
login; the existing durable API write limiter remains active across restarts.

هذا الوضع يثق بمستخدم نظام التشغيل والبرامج المحلية، ولا يصلح لجهاز مشترك
غير موثوق أو مستخدمين مستقلين. الاتصال محصور على الجهاز، مع رفض المضيفين
والطلبات الخارجية والترويسات الوسيطة. لا تستخدمه خلف وكيل عكسي أو نفق أو
نشر عام. قد يتعذر تمييز وكيل محلي يحذف جميع علامات التمرير عن برنامج محلي
موثوق. للوصول عبر الشبكة استخدم هوية مُدارة. لا توجد محاولات دخول لتقييدها؛
يبقى تقييد طلبات الكتابة في الواجهة البرمجية فعّالًا بعد إعادة التشغيل.

# Local Miyaar setup / تشغيل معيار محليًا

This profile runs the workspace, analytics worker, local model and optional Whisper transcription on this Windows computer. Installation is one part of acceptance: it does not establish production readiness or guarantee every feature will succeed.

<div dir="rtl">

يشغّل هذا الإعداد مساحة العمل وعامل التحليلات والنموذج المحلي وتفريغ الصوت الاختياري عبر Whisper على جهاز Windows هذا. التثبيت جزء من التحقق؛ لا يثبت الجاهزية للإنتاج ولا يضمن نجاح كل ميزة.

</div>

## Start / البدء

Open PowerShell in the repository root. Use the project virtual environment; Node.js 24 and npm must be on `PATH` for installation/build.

<div dir="rtl">

افتح PowerShell في جذر المستودع. استخدم بيئة Python الخاصة بالمشروع، واجعل Node.js 24 وnpm متاحين في `PATH` للتثبيت والبناء.

</div>

```powershell
$env:PYTHONUTF8 = '1'
.\.venv\Scripts\python.exe scripts/local_runtime.py doctor
# Reproduce dependencies, download pinned voice weights, and build the frontend:
.\.venv\Scripts\python.exe scripts/local_runtime.py install --voice --agents
# Start the local server and its scheduled connector worker:
.\.venv\Scripts\python.exe scripts/local_runtime.py start --worker --port 8000
```

Open <http://localhost:8000>. Keep this terminal open; `Ctrl+C` stops the workspace and its worker. The server binds to `127.0.0.1`, for this computer only. Installation requires internet access; the installed local voice route loads its model without downloading files during requests. `--model-dir` can select another absolute voice-model directory for all three commands.

<div dir="rtl">

افتح <http://localhost:8000> واترك الطرفية مفتوحة. يوقف `Ctrl+C` مساحة العمل والعامل. يستمع الخادم على `127.0.0.1` لهذا الجهاز فقط. يحتاج التثبيت إلى الإنترنت؛ أما مسار الصوت المحلي فيحمّل النموذج المثبّت دون تنزيل ملفات أثناء الطلبات. يمكن اختيار مجلد مطلق آخر للنموذج باستخدام `--model-dir` مع الأوامر الثلاثة.

</div>

## Installed components / المكونات المثبتة

| Component / المكوّن | Status / الحالة |
| --- | --- |
| Python web dependencies / اعتماديات خادم Python | Installed in `.venv`; dependency consistency check passed. / مثبّتة في `.venv`، واجتازت فحص توافق الاعتماديات. |
| Ollama and local chat / المحادثة المحلية | Gemma 3 4B: installation and bilingual response acceptance in progress. / تثبيت Gemma 3 والتحقق من ردوده بالعربية والإنجليزية قيد التنفيذ. |
| Local voice / الصوت المحلي | `faster-whisper==1.2.1`, multilingual `small`, CPU INT8. / نموذج `small` متعدد اللغات، يعمل على المعالج بدقة INT8. |
| Optional agent examples / أمثلة الوكلاء الاختيارية | `langgraph==1.2.16`, `pydantic-ai-slim==2.57.0`, `mcp==2.3.0` installed. Installation alone does not select a runtime; the core does not require these frameworks. / مثبّتة؛ لا يفعّل التثبيت وحده مسار وكيل، ولا يتطلبها المحرك الأساسي. |

The selected Gemma 3 weights are subject to [Gemma's terms](https://ai.google.dev/gemma/terms). The local profile uses a bounded context and one inference model; validate model quality for your actual tasks before production.

The voice installer pins `Systran/faster-whisper-small` to revision `536b0662742c02347bc0e980a01041f333bce120`. Its default directory is `~/.cache/miyaar/models/faster-whisper-small`, outside the repository. A real English sample transcribed successfully; actual microphone capture and Arabic transcription accuracy still need device acceptance. Results and test counts have one source: [README — Testing](../README.md#testing).

<div dir="rtl">

تخضع أوزان Gemma 3 لشروط Gemma المرتبطة أعلاه. يستخدم الإعداد المحلي سياقًا محدودًا ونموذج استدلال واحدًا؛ تحقّق من جودة النموذج على مهامك الفعلية قبل الإنتاج.

يثبّت مُثبّت الصوت مراجعة النموذج المحددة أعلاه في `~/.cache/miyaar/models/faster-whisper-small` خارج المستودع. نجح تفريغ عينة إنجليزية فعلية؛ ما زال تسجيل الميكروفون الحقيقي ودقة التفريغ العربي يحتاجان اختبارًا على الجهاز. النتائج وأعداد الاختبارات موثقة في [قسم الاختبارات في README](../README.md#testing).

</div>

Existing Docker and standalone FFmpeg installations are optional for this profile. Whisper uses PyAV's bundled decoding libraries. No NVIDIA/CUDA hardware was detected, so this profile uses CPU inference. LLMRouter and its large Torch/CUDA dependency stack were not installed.

<div dir="rtl">

لا يتطلب هذا الإعداد تثبيتات Docker أو FFmpeg المستقلة الموجودة على الجهاز؛ يستخدم Whisper مكتبات فك الصوت المضمنة مع PyAV. لم يُكتشف عتاد NVIDIA/CUDA، لذلك يعمل الاستدلال على المعالج. لم تُثبّت حزمة LLMRouter واعتماديات Torch/CUDA الكبيرة.

</div>

## Voice operation and limits / استخدام الصوت وحدوده

- The UI uses local Whisper when the server reports it available; otherwise browser speech controls remain available where supported. Allow microphone access in a supported browser on localhost or HTTPS. Browser speech may use the browser vendor's service; it has a separate consent notice.
- Local recording stops after 29 seconds to remain below the server's 30-second limit. The maximum upload is 2,000,000 bytes. One transcription runs at a time per server process; another request receives a busy response.
- Audio and transcription output are not persisted by the transcription route. The recording is sent to this Miyaar server. Recognized text goes into an editable draft and is never sent as a chat message automatically; sending it creates the normal conversation record.
- Cancel closes capture and ignores a late result. It does not interrupt a CPU transcription already running on the server. Read-aloud uses the browser's installed voices; Arabic voice quality depends on the device.

<div dir="rtl">

- تستخدم الواجهة Whisper المحلي عندما يعلن الخادم توفره، وإلا تظهر أدوات صوت المتصفح عند دعمها. اسمح بالميكروفون في متصفح مدعوم على localhost أو HTTPS. قد يستخدم صوت المتصفح خدمة المورّد، وله إشعار موافقة مستقل.
- يتوقف التسجيل المحلي بعد 29 ثانية للبقاء دون حد الخادم البالغ 30 ثانية. حد الرفع 2,000,000 بايت. يعالج كل خادم عملية تفريغ واحدة في الوقت نفسه ويعيد حالة «مشغول» للطلب الآخر.
- لا يحفظ مسار التفريغ الصوت أو النص الناتج. يُرسل التسجيل إلى خادم معيار هذا، ويُضاف النص إلى مسودة قابلة للتعديل دون إرسال تلقائي. عند إرسال المسودة تُحفظ ضمن سجل المحادثة المعتاد.
- يوقف الإلغاء التسجيل ويتجاهل النتيجة المتأخرة، لكنه لا يقطع عملية التفريغ التي بدأت على معالج الخادم. تستخدم القراءة الصوتية أصوات المتصفح المتاحة، وتعتمد جودة العربية على الجهاز.

</div>

## Cloud setup and acceptance / إعداد السحابة والتحقق

`doctor` reports installed packages and model presence; it is not a successful conversation or speech test. Check a real English and Arabic conversation, microphone recording, editable transcript, denied permission, retry, upload-to-report flow, approval, and restart before accepting the installation. Keep the model's actual failure/fallback status visible.

Hosted Supabase identity and PostgreSQL require protected server configuration and a real deployment check; local installation does not create cloud accounts, organizations, subscriptions or billing. Follow [.env.example](../.env.example) and [known limitations](KNOWN_LIMITATIONS.md). Supply secrets through protected environment settings, never API-key messages in chat or tracked files. A model listening on this computer is not reachable from a hosted server automatically.

The installed Codex skills `gh-fix-ci`, `gh-address-comments`, `transcribe`, `speech`, `security-best-practices`, and `security-threat-model` become available on your next Codex turn. They assist development; they are not SaaS runtime features or subscriptions.

<div dir="rtl">

يعرض `doctor` الحزم المثبّتة ووجود النموذج؛ لا يثبت نجاح المحادثة أو الصوت. قبل قبول التثبيت، اختبر محادثة فعلية باللغتين، وتسجيل الميكروفون، وتعديل النص، ورفض الإذن، وإعادة المحاولة، ومسار رفع البيانات إلى التقرير والموافقة وإعادة التشغيل. أبقِ حالة فشل النموذج أو الانتقال للرد البديل واضحة.

تحتاج هوية Supabase وقاعدة PostgreSQL المستضافتان إعدادًا محميًا للخادم واختبار نشر فعليًا. لا ينشئ التثبيت المحلي حسابات السحابة أو المؤسسات أو الاشتراكات أو الفوترة. اتبع ملف الإعداد النموذجي والقيود المعروفة المرتبطين أعلاه، وضع الأسرار في إعدادات البيئة المحمية، ولا ترسل مفاتيح API في المحادثة أو تحفظها في ملفات متتبعة. لا يستطيع الخادم المستضاف الوصول تلقائيًا إلى نموذج يعمل على هذا الجهاز.

تتوفر مهارات Codex المذكورة أعلاه في رسالتك التالية إلى Codex. تساعد في التطوير ولا تمثل ميزات تشغيلية أو اشتراكات داخل المنصة.

</div>

Upstream references / المصادر الأصلية: [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [Ollama Gemma 3](https://ollama.com/library/gemma3:4b).

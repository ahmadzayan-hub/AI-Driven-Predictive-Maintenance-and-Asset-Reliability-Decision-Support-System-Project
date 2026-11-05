# Langflow MCP example using temporary synthetic data

This example prepares an optional Langflow MCP connection without registering
one. It reuses Miyaar's restricted MCP transport and creates a fresh, temporary
sample workspace each time it is started. It does not connect to the website,
the owner's files, an existing database, a model or an external API.

## What it demonstrates

- Generate the MCP server JSON shape consumed by Langflow's MCP settings.
- Discover and call only `help`, `run_status` and `explain_report`.
- Read a deterministic synthetic report that stops at the existing human
  approval gate. Approval, publication, new runs and memory tools are not exposed.
- Keep the application, Hermes profile, active workflows and dependencies unchanged.

This is an MCP server example, **not a Langflow flow export or an installed
connection**. Langflow itself has not been installed or run for this example.
An MCP SDK handshake is not a test of Langflow's UI, authentication, permissions,
graph wiring or component execution. Current verification is in
[README testing](../../README.md#langflow-synthetic-mcp-example).

## Review before using

Inspect `miyaar_synthetic.py` and the existing `scripts/hermes_mcp.py`. Use an
already-reviewed local Python interpreter and checkout. From the repository:

```sh
python -I -B -X utf8 examples/langflow/miyaar_synthetic.py --print-config
python -I -B -X utf8 examples/langflow/miyaar_synthetic.py --print-config --language ar
```

These commands only print JSON with absolute paths for the current interpreter
and script. They do not launch the MCP server, write a profile, register a server
or contact Langflow. Do not commit the generated machine-specific configuration.
Do not copy it into `.mcp.json`, `mcp.json` or an automatic settings location.

After separate operator approval, that JSON can be reviewed in a locally hosted,
authenticated Langflow instance's MCP server configuration. Importing, selecting
or refreshing a server can immediately launch it for discovery. **A `disabled`
field does not prevent this: Langflow's importer drops unknown fields.** Use a
unique server name if an existing saved name would resolve to another config.

Select the `MCPTools` component's synthetic server and one listed tool. No Agent,
model, model credentials or hosted recipient is needed to examine this example.
Do not connect the output to a model without separately approving that recipient.
If administrative stdio restrictions or interpreter hardening reject the command,
stop and ask the operator; do not weaken those settings.

## Boundaries

- `--serve-synthetic` is explicit. There is no path, workspace, provider or config
  input. Other arguments are rejected before storage is opened.
- Serving creates SQLite schema/WAL and a sample report in a fresh temporary
  directory. It is not a read-only database connection. Normal shutdown
  closes and removes this directory; an abrupt process kill may leave temporary
  synthetic files for the operating system to clean up.
- Each process has a new sample run and run ID. Use the tools' default latest
  sample; do not reuse a run ID from a previous connection.
- Inherited application/provider settings are cleared in the child process.
  A Python audit guard refuses socket connections/listeners and subprocesses.
  This is defense in depth, not an operating-system sandbox for untrusted code.
- The example uses the deterministic engine and no model. It never approves or
  publishes its report and does not expand the existing tool allowlist.
- Using real Miyaar data is outside this example. Even the existing restricted
  launcher reads a configured memory file and initializes SQLite schema/WAL at
  startup; that needs separately scoped permission. See
  [Hermes preparation](../../docs/HERMES_DESKTOP.md).

## Pinned compatibility evidence

The configuration shape was reviewed against Langflow **v1.13.1**, source commit
`d125bea3847e5992e287550d0fb1a0926f49be2a`:

- [JSON import parser](https://github.com/langflow-ai/langflow/blob/d125bea3847e5992e287550d0fb1a0926f49be2a/src/frontend/src/utils/mcpUtils.ts#L17-L102)
- [MCPTools server resolution](https://github.com/langflow-ai/langflow/blob/d125bea3847e5992e287550d0fb1a0926f49be2a/src/lfx/src/lfx/components/models_and_agents/mcp_component.py#L384-L556)
- [Stdio client parameters](https://github.com/langflow-ai/langflow/blob/d125bea3847e5992e287550d0fb1a0926f49be2a/src/lfx/src/lfx/base/mcp/util.py#L2198-L2287)
- [Interpreter restrictions](https://github.com/langflow-ai/langflow/blob/d125bea3847e5992e287550d0fb1a0926f49be2a/src/lfx/src/lfx/base/mcp/security.py#L465-L518)

The generated wrapper belongs to MCP server settings. It is not the component's
`mcp_server` input; that input resolves a saved name or a `{name, config}` object,
and an existing database configuration takes precedence. No guessed flow JSON
is supplied or described as import-tested.

## العربية

هذا مثال اختياري لربط Langflow عبر MCP باستخدام بيانات تجريبية مصطنعة فقط.
لم يُثبّت Langflow ولم تُسجّل أي وصلة. أمر `--print-config` يطبع الإعدادات
فقط، ولا يشغّل الخادم أو يغيّر ملفات الحساب. لا تحفظ الناتج في ملفات الإعداد
التلقائي ولا ترفعه إلى Git لأنه يحتوي على مسارات الجهاز.

استيراد الإعداد أو اختياره في Langflow قد يشغّل الخادم فوراً لاكتشاف الأدوات.
الحقل `disabled` لا يمنع ذلك لأن المستورد يتجاهله. يلزم اعتماد المشغّل قبل
الاستيراد؛ لا تتجاوز قيود المدير أو حماية تشغيل المفسّر. لم يُختبر الاستيراد
أو التنفيذ داخل Langflow، واختبار بروتوكول MCP لا يثبت ذلك.

التشغيل الصريح ينشئ قاعدة SQLite مؤقتة وتقريراً تجريبياً حسابياً، ويتوقف عند
بوابة الموافقة البشرية. الأدوات المتاحة هي المساعدة وحالة التحليل وشرح التقرير
فقط. لا نشر ولا اعتماد ولا تشغيل نموذج، ولا قراءة لبيانات العمل الحقيقية.
إعداد قاعدة البيانات قد يكتب مخططها وملفات WAL، ثم تُحذف الملفات المؤقتة عند
الإغلاق الطبيعي. قد تبقى ملفات مصطنعة مؤقتة إذا أُوقفت العملية قسراً.

ابدأ باللغة العربية عبر `--language ar`. كل اتصال جديد ينشئ تحليلاً جديداً؛
لا تعِد استخدام معرف تحليل من اتصال سابق. لا توصل الناتج بنموذج أو جهة خارجية
ولا تضف بيانات حقيقية دون موافقة مستقلة تحدد النطاق والجهة المستقبلة.

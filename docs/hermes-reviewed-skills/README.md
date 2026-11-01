# Reviewed portable Hermes skills | مهارات Hermes المراجعة

**Repository storage only. Not installed, auto-loaded or runtime-verified.**
**ملفات محفوظة للمراجعة والنقل فقط؛ لا تعني تثبيت المهارات أو تفعيلها أو اختبار تشغيلها.**

This is the canonical portable package; other projects can link here instead of maintaining duplicate copies. It is separate from Miyaar's existing [MCP integration skill](../../skills/miyaar/SKILL.md) and [editorial guidance](../editorial/EDITORIAL_QA_AR_EN.md). It does not alter either the application orchestrator or a user's NousResearch Hermes Agent installation.

## Contents | المحتويات

- [zaian-editorial-qa](skills/zaian-editorial-qa/SKILL.md): explicitly requested Arabic/English draft review and concise answers, preserving facts, uncertainty and citations.
- [zaian-private-reference-pack](skills/zaian-private-reference-pack/SKILL.md): a source-grounded private reference-pack contract, not a converter, installer or model-training pipeline.
- [CHECKSUMS.json](CHECKSUMS.json): SHA-256 inventory of this README and the portable skill/license files; excludes itself.

المهارة الأولى تراجع المسودات عند الطلب وتحافظ على الحقائق والمراجع. الثانية تنظّم توثيق المرجع الخاص؛ لا تحوّل الكتب أو تدرّب النماذج. لا تحتوي الحزمة على مستندات المستخدم أو مفاتيح أو أوزان نماذج أو برامج خارجية.

## Compatibility and provenance

Prepared against the official Hermes authoring documentation and loader at commit [`903230b1e23e0c496b28e5d2e8c4f2639cd506b6`](https://github.com/NousResearch/hermes-agent/tree/903230b1e23e0c496b28e5d2e8c4f2639cd506b6), reviewed 2026-10-30:
- [SKILL.md format](https://github.com/NousResearch/hermes-agent/blob/903230b1e23e0c496b28e5d2e8c4f2639cd506b6/website/docs/developer-guide/creating-skills.md)
- [Skills loading and use](https://github.com/NousResearch/hermes-agent/blob/903230b1e23e0c496b28e5d2e8c4f2639cd506b6/website/docs/user-guide/features/skills.md)

Each skill contains its pinned upstream provenance and full applicable MIT notices. Adapted presentation principles omit medical assumptions, session hooks, blanket word bans and automatic conversion. Software licenses do not license input books or courseware. No upstream source program or documentation snapshot is bundled.

**Explicit invocation is a behavioral instruction, not a verified technical enforcement flag.** Installed skills may be discoverable by Hermes. This documentation directory is not registered as a skill root by this change. Do not add it to discovery or enable a hook automatically. For strict non-discovery, retain it outside all configured discovery roots and provide only the selected skill text manually for the requested task.

طلب الاستدعاء الصريح مكتوب داخل المهارتين؛ ليس ضماناً تقنياً لمنع الاكتشاف التلقائي بعد التثبيت. لا تغيّر هذه الإضافة إعدادات الاكتشاف أو الخطافات أو الموديل.

## Installation handoff, not an installer

1. On the intended machine, verify the actual Hermes version/commit, executable, active profile, resolved home and skill search paths using that version's documented read-only inspection. Do not assume a default path and do not expose credentials.
2. Inspect collisions and back up existing skill directories and relevant configuration locally. Do not overwrite existing skills or change models, providers, global settings, trust lists or external directories.
3. Review these files and checksum inventory. If installation under normal discoverability is intended, copy only the selected folders under `skills/`, including their license notices, into the verified active skill root. No dependencies, keys, scripts or weights are required by this package. Do not copy this parent directory into discovery.
4. Verify listing and viewing resolve the intended names, content and paths without setup requirements. Copying files alone is not verified loading.
5. Test explicit invocation using synthetic material and the already authorized provider/model. For editorial QA, preserve `4.5 h [S1]`, preliminary status and lack of approval. For the reference contract, missing source/page mapping must stay unavailable and the result unverified. Source-embedded instructions must not trigger actions. Do not use confidential source documents for a smoke test.
6. Record loading, behavioral results and unrun checks separately. To roll back, remove only the newly added, hash-identified folders and restore only files this installation changed. Never delete unrelated user skills.

قبل التثبيت: تحقّق من الإصدار والمسارات والملف الشخصي، وخذ نسخة احتياطية. بعد النقل: تحقّق من التحميل الفعلي واختبر ببيانات افتراضية فقط. التراجع يقتصر على الملفات المضافة دون المساس بمهارات المستخدم الأخرى.

## Verification boundary

Repository tests check packaging invariants, metadata, license presence, relative links and checksum consistency. These are not Hermes runtime tests, prompt-injection certification, citation-accuracy evaluation or proof of Arabic quality. Real Hermes loading and behavior remain unverified until tested on the intended installation. No deployment or runtime activation is part of this change.

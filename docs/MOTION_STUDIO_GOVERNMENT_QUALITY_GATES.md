# Motion Studio: Dubai Government Content & Technical Quality Gates

Status: **engineering draft only**, not an approved government compliance assessment.

## Verified public reference points
- Government of Dubai Executive Council Resolution No. 47 of 2025 approving the Government Communication Guide (https://dlp.dubai.gov.ae/Legislation%20Reference/2025/Executive%20Council%20Resolution%20No.%20%2847%29%20of%202025%20Approving%20Communication%20Guide.html). In particular, human evaluation of AI-generated visual/written work, data protection, intellectual-property rights and compliance with applicable Dubai Digital Authority rules.
- Dubai Government Websites Excellence Model (https://www.digitaldubai.ae/docs/default-source/default-document-library/dubai-government-websites-excellence-model_en.pdf): bilingual Arabic/English guidance for government websites and file accessibility. Not a replacement for RTA's controlled audiovisual brand manual.
- UAE National Digital Accessibility Policy (https://u.ae/en/about-the-uae/strategies-initiatives-and-awards/policies/government-services-and-digital-transformation/national-digital-accessibility-policy).

Do not claim any of these sources approves a specific RTA motion template, engineering analysis, statistics or video release. Obtain the controlled RTA/Dubai brand, communications, statistical publication, cybersecurity and accessibility requirements before official certification.

## Release gates: all must have independent evidence
1. **Statistics and analytics:** Every source KPI names dataset, scope/grain, reporting period, formula, units, data status, revision and calculation; uncertainty visible where applicable. Causal and financial claims explicitly reviewed. Any missing statistic blocks official release.
2. **RTA engineering review:** Technical geometry, train routes, failure claims, safety/cyber/maintenance statements and contractual references checked by authorized specialists.
3. **Human creative and language QA:** Arabic connected letters and RTL, diacritics where necessary, Latin technical IDs isolated; English correct; licensed typeface/brand/imagery; verified captions; audio/narration script checked.
4. **Automated media QA:** Real H.264 MP4, yuv420p, constant 30fps, permitted resolution; AAC 48kHz where voice present; frame/audio runtime agreement; no blank or corrupted media; end card not truncated.
5. **Confidentiality:** Local or explicitly approved tenant-isolated rendering. No silent external LLM, image/audio generator, cloud upload, public URL, or telemetry. Review data loss and retention before enabling any cloud provider.
6. **Rights and publication:** Copyright, likeness, recorded-voice consent, images and music licensed; human reviewer and actual issuance permission from host auth; exact content hash reviewed, approval invalidates on edit. The current review utility returns only `RELEASE_ELIGIBLE_FOR_HOST_DECISION`, never issues.
7. **QA results:** Tests and actual video listening/inspection, browser EN/AR desktop/mobile, approved storage/backup/restore and versioned release records.

## Agents and LLM integration contract
Introduce agents only as narrow specialist *drafting or checking* stages that return structured data and traceable evidence: Storyboard Planner, Source/Statistics Verifier, Arabic/English Language Checker, Technical Accuracy Checker, Media QA Inspector, Independent Governance Reviewer. Keep deterministic validations independent of LLM opinions. Any LLM use requires explicitly configured approved provider, data minimization, consent/policy clearance, no source text as instructions, per-request time/token budget, schema validation, logging without private content and human review.

## Implementation status
Implemented: offline draft browser editor; authorized source/run storyboard export; FFmpeg/Pillow-based local renderer; MP4 inspection script; fail-closed human-review eligibility check. **Not implemented:** authenticated queue/worker deployment, persistent tenant artifact storage, media-provenance signing, host approval API integration, actual published RTA workflow, optional LLM provider, approval-controlled media distribution. CI and rendered Arabic/English end-to-end evaluation must pass before calling the system release-ready.

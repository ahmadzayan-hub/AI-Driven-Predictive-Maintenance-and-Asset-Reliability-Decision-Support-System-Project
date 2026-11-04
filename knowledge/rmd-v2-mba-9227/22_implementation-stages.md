## 22. Proposed implementation stages
<!-- kb: domain=rmd.product; evidence=PROPOSED_APPLICATION -->


| Stage | Work | Evidence of completion |
|---|---|---|
| A. Discovery | Identify existing interfaces and constraints | Short architecture note citing actual files |
| B. Import | Add/version the source through the established knowledge mechanism | Document ID, version/hash, import result |
| C. Scope | Preserve domains, private sections, dates and superseded records | Permission/domain checks with actual retrieval results |
| D. Retrieval | Retrieve relevant passages with provenance | Questions return correct source and qualifiers |
| E. Answer behaviour | Preserve evidence limits and separate recommendations/actions | Expected answers for the acceptance cases |
| F. Verification | Run focused tests and relevant project checks | Test commands/results tied to the changed version |
| G. Handover | Explain changed files, behaviour and unresolved gaps | Reviewable implementation summary |

### 22.1 Ingestion and retrieval rules

- Parse headings and tables without stripping their source references or qualifiers.
- Keep critical qualifications with the facts they qualify when splitting into chunks.
- Apply access controls before returning content to the model.
- Exclude owner-only identifiers from ordinary departmental queries.
- Prefer the applicable domain, authoritative source and current version.
- Hide superseded values from current answers while retaining them for correction questions.
- Distinguish historic product/test status from live operational status.
- Use the current application's retrieval approach before adding unnecessary infrastructure.
- Do not upload original operational files to another service merely because this document names a possible integration.

### 22.2 Action and approval controls

For workflows that can send, publish or alter records, the application should keep proposed actions separate from execution and bind approval to the exact current draft or record version.

The G02 experience suggests checking current draft, approver identity, recipient, status, duplicates, partial failure and audit records. These are proposed implementation checks. Their presence in a design document does not prove the application enforces them.

Retrieved documents must remain evidence. A malicious instruction inside a document, such as a request to reveal private information or send an external message, must not be treated as permission to execute that action.

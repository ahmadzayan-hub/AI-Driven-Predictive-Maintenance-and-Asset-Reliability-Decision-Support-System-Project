## 12. Source register and reproducibility
<!-- kb: domain=meta.sources -->


All PDF locators use **one-based physical PDF page numbers**, unless a source explicitly names a printed page. DOCX references use section names because layout pagination can vary.

The source register follows below. SRC-18/SRC-20, SRC-21/SRC-22 and SRC-24/SRC-25 are exact binary duplicates. Other similarly titled course files are distinct versions and have been retained.

CALC-01 is the deterministic audit in sections 4-6 of SRC-28 and SRC-29, carried out on 5 November 2026. USER-REQ refers to the user's current project instructions. HIST-01 to HIST-03 refer only to earlier conversation context available for this handover.

WEB-01: Anthropic. (n.d.). *How Claude remembers your project*. Claude Code documentation. Retrieved 5 November 2026 from https://code.claude.com/docs/en/memory. Used only for the concise file-loading guidance in section 9.


### 12.1 Source inventory

These links point to the exact source copies used. They require the owner's authorised access. Copy relevant sources into the approved project environment when the application needs their bytes.

| ID | Original source file | Extent | Classification / canonical source |
| --- | --- | --- | --- |
| SRC-01 | 1. Business Analytics for Decisions Making(1).pdf (private file; see the owner's library) | 21 PDF pages | Course teaching material |
| SRC-02 | 5. Practical Applications in Various Business Sectors (1)(1).pdf (private file; see the owner's library) | 44 PDF pages | Course teaching material |
| SRC-03 | 10. Creating Competitive Advantage through Analytics(1).pdf (private file; see the owner's library) | 27 PDF pages | Course teaching material |
| SRC-04 | 4. Building a Business Analytics Competency Center(1).pdf (private file; see the owner's library) | 29 PDF pages | Course teaching material |
| SRC-05 | 5. Practical Applications in Various Business Sectors(2).pdf (private file; see the owner's library) | 35 PDF pages | Course teaching material |
| SRC-06 | 8. Decision-Making Support through Analytics_V2_21122024(1).pdf (private file; see the owner's library) | 30 PDF pages | Course teaching material |
| SRC-07 | 3. Business Analytics Strategies and Processes(1).pdf (private file; see the owner's library) | 45 PDF pages | Course teaching material |
| SRC-08 | 2. The Role of AI and Machine Learning in Business(1).pdf (private file; see the owner's library) | 33 PDF pages | Course teaching material |
| SRC-09 | AIB902-Lecture-5(1).pdf (private file; see the owner's library) | 17 PDF pages | Course teaching material |
| SRC-10 | 1-Introduction-to-Business-Analytics(1).pdf (private file; see the owner's library) | 32 PDF pages | Course teaching material |
| SRC-11 | AIB902-Lecture-8(1).pdf (private file; see the owner's library) | 18 PDF pages | Course teaching material |
| SRC-12 | AIB902-Lecture-7(1).pdf (private file; see the owner's library) | 24 PDF pages | Course teaching material |
| SRC-13 | AIB902-Lecture-6(1).pdf (private file; see the owner's library) | 22 PDF pages | Course teaching material |
| SRC-14 | 3-Business-Analytics-Strategies-and-Processes(1).pdf (private file; see the owner's library) | 32 PDF pages | Course teaching material |
| SRC-15 | 4-Building-a-Business-Analytics-Competency-Center(1).pdf (private file; see the owner's library) | 32 PDF pages | Course teaching material |
| SRC-16 | 2-The-Role-of-AI-and-Machine-Learning-in-Business(1).pdf (private file; see the owner's library) | 32 PDF pages | Course teaching material |
| SRC-17 | AIB902-Lecture-9(1).pdf (private file; see the owner's library) | 24 PDF pages | Course teaching material |
| SRC-18 | Corea An introduction to data(1).pdf (private file; see the owner's library) | 131 PDF pages | Reference book |
| SRC-19 | Ahmed_Zaian_Student_Analytics_Profile_Gp_MK_9226(1).docx (private file; see the owner's library) | DOCX | Professional learning profile |
| SRC-20 | introduction-to-data-everything-you-need-to-know-about-ai-big-data-and-data-science(1).pdf (private file; see the owner's library) | 131 PDF pages | Reference book; exact alias of SRC-18 |
| SRC-21 | Bernard_Marr Key Business Analytics(1).pdf (private file; see the owner's library) | 276 PDF pages | Reference book |
| SRC-22 | Bernard_Marr_Key_Business_Analytics_The(1).pdf (private file; see the owner's library) | 276 PDF pages | Reference book; exact alias of SRC-21 |
| SRC-23 | Gert and Jesper_Business analytics for Managers(1).pdf (private file; see the owner's library) | 291 PDF pages | Reference book |
| SRC-24 | Judah Building a Digital Analytics Organization(1).pdf (private file; see the owner's library) | 354 PDF pages | Reference book |
| SRC-25 | Building a Digital Analytics Organization Create Value by Integrating Analytical Processes, Technology(1).pdf (private file; see the owner's library) | 354 PDF pages | Reference book; exact alias of SRC-24 |
| SRC-26 | Group_9226_Student_Analytics_Readiness.pdf (private file; see the owner's library) | 25 PDF pages | Readiness/project proposal |
| SRC-27 | Group_9226_Team_3_Project_Publication.docx (private file; see the owner's library) | DOCX | Team 3 publication |
| SRC-28 | Group_9226_Team_3_Enterprise_Dataset.csv (private file; see the owner's library) | 5,000 rows × 60 fields | Original synthetic data |
| SRC-29 | Group_9226_Team_3_Analytics_Workbook.xlsx (private file; see the owner's library) | 6 worksheets | Source workbook snapshot |

### 12.2 SHA-256 manifest

Hash equality proves the duplicate-file relationships recorded here. A changed hash requires version review before reusing this audit's expected numbers.

~~~json
[
  {"source_id": "SRC-01", "sha256": "4da897c7e8f18d3ade96fd234d16663541a6b1fcbbdf9b3f7532f3fe2eb70a39", "canonical_source_id": "SRC-01"},
  {"source_id": "SRC-02", "sha256": "6d97265c3f961229f7133fc5eae8873d8a947b5529b05508c63fa124dce2800f", "canonical_source_id": "SRC-02"},
  {"source_id": "SRC-03", "sha256": "8754093049539c1cb2c9759b5ffcf31a1d13c3cb7114240d106f0124e00f5950", "canonical_source_id": "SRC-03"},
  {"source_id": "SRC-04", "sha256": "586c4fadd2f5ca38571c693948c14cfb5843e06ab0bac50aa04af169b2a39fc3", "canonical_source_id": "SRC-04"},
  {"source_id": "SRC-05", "sha256": "b70c4dc7dffeebed4b773b6f4ed8ca8b85f786061259fc6308d4ed0c2b25fd7c", "canonical_source_id": "SRC-05"},
  {"source_id": "SRC-06", "sha256": "8698329e35cc79920a42490aebe5d4a37cd7fc250bb84a2215882725894b0a79", "canonical_source_id": "SRC-06"},
  {"source_id": "SRC-07", "sha256": "326ab044f01053089858faf975c404b7d1ea9eaf4d050f8e0bc0b57aa509b1b4", "canonical_source_id": "SRC-07"},
  {"source_id": "SRC-08", "sha256": "4aeab858dc62cfa547a15f5239125c38fbe76501f391cc54387572b481b8a31c", "canonical_source_id": "SRC-08"},
  {"source_id": "SRC-09", "sha256": "2cc04c06a0f344633e8a43685d3cc45e769379621163185d2fd938d459e7141b", "canonical_source_id": "SRC-09"},
  {"source_id": "SRC-10", "sha256": "d1129aee67a2c858f5f4564d0e4c4710bfef3ead822a00f7109d89b5d9503c7a", "canonical_source_id": "SRC-10"},
  {"source_id": "SRC-11", "sha256": "74eb1adf4e2330943f2282c3de3bca8807e1f9a0a50167eca5be0ce3192147b1", "canonical_source_id": "SRC-11"},
  {"source_id": "SRC-12", "sha256": "841432e84cca077eab00123a5e0246835d66d33408f1d62fc34440495192caad", "canonical_source_id": "SRC-12"},
  {"source_id": "SRC-13", "sha256": "821f34a5741e3a3b7e41d4b332beea4a4210f06db49df16a161d7185a1a1bfa1", "canonical_source_id": "SRC-13"},
  {"source_id": "SRC-14", "sha256": "c27c7e82dfa2e21d6577d106b0bad77e406b1bd2040d3b9f46fae35957e13bd2", "canonical_source_id": "SRC-14"},
  {"source_id": "SRC-15", "sha256": "4bca15d06bd9538584662b35fbb1b127e5d6a9625a78cd6a403904b92fed25c8", "canonical_source_id": "SRC-15"},
  {"source_id": "SRC-16", "sha256": "2e5b9f7e7a82fe26ef55a52b4d56d0c8ca9ea02cc0eec0a9ff38752e89569566", "canonical_source_id": "SRC-16"},
  {"source_id": "SRC-17", "sha256": "195dd29051326705c2d06eebcaf93f035d0a4c5d854b978d6e3b3405a528ab10", "canonical_source_id": "SRC-17"},
  {"source_id": "SRC-18", "sha256": "178c3a1be3debcf11537cb0a54e7f3e4cbadc981297a876d35e454e497a622ab", "canonical_source_id": "SRC-18"},
  {"source_id": "SRC-19", "sha256": "cc1e84b2fb31404431addd304c30f8bef4fac11322f63e3f9c3920cadf15831a", "canonical_source_id": "SRC-19"},
  {"source_id": "SRC-20", "sha256": "178c3a1be3debcf11537cb0a54e7f3e4cbadc981297a876d35e454e497a622ab", "canonical_source_id": "SRC-18"},
  {"source_id": "SRC-21", "sha256": "ce95d994b7c8037cdd0fa93fd2c692680377c4268e1093e2e1ffad46c431df82", "canonical_source_id": "SRC-21"},
  {"source_id": "SRC-22", "sha256": "ce95d994b7c8037cdd0fa93fd2c692680377c4268e1093e2e1ffad46c431df82", "canonical_source_id": "SRC-21"},
  {"source_id": "SRC-23", "sha256": "3fec5924d9ebe38e1988291f1bd199ab8b05b0f1beea93729b32249a916b4f44", "canonical_source_id": "SRC-23"},
  {"source_id": "SRC-24", "sha256": "5d3d17f6ff1603d5ea6b0f020b4972e7b757fdfa8a6c295d5fd0887162fad036", "canonical_source_id": "SRC-24"},
  {"source_id": "SRC-25", "sha256": "5d3d17f6ff1603d5ea6b0f020b4972e7b757fdfa8a6c295d5fd0887162fad036", "canonical_source_id": "SRC-24"},
  {"source_id": "SRC-26", "sha256": "7f8e31260eedb841a976502d6c288031cebb5f4b29ec51ab6f13bbac756ab32f", "canonical_source_id": "SRC-26"},
  {"source_id": "SRC-27", "sha256": "cc9a79983e634ad3e04e645ba4880d72feb549f40e443776436e59c04f6697f5", "canonical_source_id": "SRC-27"},
  {"source_id": "SRC-28", "sha256": "1eb08b41a755edf4890f4fc2b4f2e10faf39f1f437be5d488b485fc55c6d21bf", "canonical_source_id": "SRC-28"},
  {"source_id": "SRC-29", "sha256": "08b9625b0b1e6d158ad58ab87a449e23e47a4a327e331bdce3385f0b0a2f252d", "canonical_source_id": "SRC-29"}
]
~~~

### 12.3 Evidence not included in this handover

The source collection does not include an inspected current RMD V2 checkout, a corrected MIYAAR dataset and transformation log, fitted prediction models or held-out predictions, an independently approved KPI/SLA catalogue, a complete final grading rubric, current LMS deadlines, or the complete runnable WWI/LDD example and four prompt-template files referenced by the lectures. Their absence from this pack does not prove that they do not exist elsewhere.

The master source summaries are original paraphrases. Use the linked originals and page locators for deeper study and exact source interpretation. Historical company examples and textbook technology descriptions need current primary-source verification before factual reuse.

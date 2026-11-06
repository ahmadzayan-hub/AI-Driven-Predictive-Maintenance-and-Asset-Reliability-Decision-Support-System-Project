# Readable download names

Date: 2026-11-06 · Status: Accepted · Owner decision: "Yes, rename them", applying the owner's file naming rules of the same day

## Context

Downloads were named for machines: `miyaar-executive-<run>-en.docx`,
`<goal>-<run>-cleaned.csv`, `agentic-os-export.json`, `INTERNAL-DRAFT-<job>.mp4` and
`<run>-<language>-<snapshot>-video.mp4`. The owner's naming rules ask for clear, natural
names with no underscores, hyphens or filler words.

## Decision

1. One module, `server/downloads.py`, names every download:

   | Download | Name |
   | --- | --- |
   | Executive brief, HTML or Word | `Executive Brief English.html`, `Executive Brief Arabic.docx` |
   | Executive slides | `Executive Slides English.html` |
   | Executive film and its files | `Executive Film Arabic.mp4`, `.vtt`, `.srt`, `Executive Film Arabic Manifest.json` |
   | Cleaned analysis table | `Cleaned Data.csv` |
   | Session export | `Session Export.json` |
   | Motion draft preview | `Internal Draft.mp4` |

2. The language is a word in the name; the run, language and snapshot stay recorded
   inside each file, so a renamed or moved file remains traceable.
3. Every header carries the quoted plain name and the RFC 5987 encoded one, so browsers
   keep the spaces. No run identifier reaches a name, which also removes the path where a
   hostile identifier had to be cleaned.
4. The interface's fallback names and its "downloaded as" message use the same names in
   English and Arabic.

## Consequences

- Two downloads of different runs in one folder now get the browser's own suffix
  ("Executive Brief English (1).docx"); the file's contents say which run it is.
- Tests changed with the names: the executive, cleaned-data and session names, the header
  encoding, and the three end-to-end downloads.
- The evidence-pack download keeps the name of the source file the user uploaded.

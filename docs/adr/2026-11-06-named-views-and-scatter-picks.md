# Several named views, and scatter points that can be picked

Date: 2026-11-06 · Status: Accepted · Owner request: "Continue next developments till complete the platform"; the gap analysis listed several named views per dataset and clickable scatter points

## Decision

1. **Named views.** Beside the one default view per owner and dataset, an owner may keep
   up to 10 named views of a dataset: `GET /api/runs/{id}/views`, `PUT` and `DELETE
   /api/runs/{id}/views/{name}`. A name is 1 to 40 characters with spaces collapsed;
   the page and address are validated exactly as the default view's are. Each named
   view is a row of the existing table keyed by the dataset's key plus `#view:` and the
   name, so the table and its unique key are unchanged and no hosted migration is
   needed. The dashboard bar has a list to open one, a name field with "Save as named
   view", and "Delete named view" for the one chosen, in English and Arabic.
2. **Scatter picks.** A click on a point in the relationship chart enlarges it and states
   its record ("Selected record: cost 9, sales 10"); when the run has a breakdown, a
   "Show only South" button narrows the page to that point's group with the same filter
   a bar click sets. The pick clears whenever the points change.

## Consequences

- Tests: the named views API on SQLite and PostgreSQL (save, list, replace, refusals in
  both languages, the limit of 10, delete), the dashboard control in both languages, and
  the scatter pick in both languages.
- The scatter's points are mouse and touch targets only; the chart's data table remains
  the keyboard path to every point's values, and the "Show only" button is a normal button.
- Not done: renaming a named view (save under the new name and delete the old one).

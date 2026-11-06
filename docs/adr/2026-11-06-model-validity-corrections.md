# Model validity corrections from the 6 November review

Date: 2026-11-06 · Status: Accepted · Owner brief: "Investigate and reproduce before fixing" four static-review leads

Each lead was reproduced with a synthetic regression test that fails on the code before
this change and passes after it. Stored results of earlier runs are not rewritten: they
were made with the earlier model card version, `2026-10-23`; cards made from today read
`2026-11-06`.

| Lead | Reproduced | Correction | Test |
| --- | --- | --- | --- |
| Feature screening and category levels chosen before the train/test split | Yes: a level present only in held-out rows became an input, and the near-copy screen read held-out outcomes | Inputs, screening and levels are re-chosen from the training rows alone (`_train_inputs`), in the regression, tree and classification stages | `test_input_choices_never_read_the_held_out_rows` |
| Missing classification outcomes treated as a known class | Yes: a blank class became the class `""` | Records with a blank named class are left out of training and testing and counted (`c_unlabelled`) | `test_blank_classes_are_left_out_not_learned` |
| Maintenance modelling reintroducing raw values the cleaner removed | Yes: a reading outside its declared limit returned as 9,999 h | A numeric value the cleaner emptied stays empty; raw values are still read for day-level dates and original text | `test_an_out_of_limits_reading_stays_out` |
| Reliability censoring at the class's latest date instead of each asset's follow-up | Yes: an asset whose records stopped in March was credited as running to December | Each asset is censored at its own last record | `test_an_asset_that_leaves_observation_is_not_credited_with_more_time` |

## What these models still are not

The classification stage scores same-record classes, and the reliability model is a
population Weibull per asset class. Neither is an individual asset's remaining-life
prediction or a validated forecast of future failure. A field-performance claim needs a
defined future-failure target and horizon, feature availability timestamps, chronological
and asset or site holdouts, calibration, false alerts per asset-month and lead time, and
outcomes adjudicated independently through the prospective shadow ledger. None of that is
claimed here.

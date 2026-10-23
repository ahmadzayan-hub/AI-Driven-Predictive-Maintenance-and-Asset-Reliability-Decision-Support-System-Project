"""The agent evaluation (ADR 0027): its arithmetic, its suites, and the
recall floors every classifying agent must keep.

The suites in evals/ are synthetic and labelled. Each has dev cases, used
to find and fix misses, and holdout cases scored before and after; the
causal and standards holdouts are not blind (ADR 0056, and the standards
cases' own source field). The text classifiers also carry a blind split,
written by an independent agent from the label definitions only and never
looked at while fixing, which the suite declares and the floors cover. A
change that drops a suite below its floor in evals/floors.json fails here.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import claims_lint  # noqa: E402
import consult  # noqa: E402
import evaluate_agents as ev  # noqa: E402
import figures_check as fc  # noqa: E402
from server import analytics, mapping, routing  # noqa: E402


class MetricsTests(unittest.TestCase):

    def test_the_confusion_matrix_and_recall_are_counted_by_hand(self):
        pairs = [("a", "a", 1), ("a", "b", 2), ("b", "b", 3), ("b", "b", 4), ("c", "a", 5)]
        labels, matrix = ev.confusion(pairs, ["a", "b", "c"])
        self.assertEqual(matrix["a"], {"a": 1, "b": 1, "c": 0})
        self.assertEqual(matrix["c"], {"a": 1, "b": 0, "c": 0})
        scores = ev.scores(labels, matrix)
        self.assertEqual(scores["per_class"]["a"]["recall"], 0.5)
        self.assertEqual(scores["per_class"]["a"]["precision"], 0.5)
        self.assertEqual(scores["per_class"]["b"]["recall"], 1.0)
        self.assertEqual(scores["per_class"]["c"]["recall"], 0.0)
        self.assertAlmostEqual(scores["macro_recall"], 0.5)
        self.assertEqual(scores["accuracy"], 0.6)

    def test_a_detector_is_judged_by_the_recall_of_what_it_must_catch(self):
        pairs = [(True, True, 1), (True, False, 2), (False, False, 3), (False, True, 4)]
        labels, matrix = ev.confusion(pairs, [True, False])
        scores = ev.scores(labels, matrix, positive=True)
        self.assertEqual((scores["recall"], scores["precision"]), (0.5, 0.5))

    def test_an_unexpected_prediction_gets_its_own_column(self):
        labels, matrix = ev.confusion([("a", "zzz", 1)], ["a"])
        self.assertEqual(labels, ["a", "zzz"])
        self.assertEqual(matrix["a"]["zzz"], 1)


class SuiteTests(unittest.TestCase):

    def test_every_suite_has_dev_and_holdout_cases_with_known_labels(self):
        for name in ev.default_suites():
            spec = ev.SUITES[name]
            with self.subTest(suite=name):
                data = json.loads((ev.EVALS / spec["file"]).read_text(encoding="utf-8"))
                self.assertTrue(data["dev"] and data["holdout"])
                if "labels" in data and name not in ("column_roles", "personal_data", "figures"):
                    allowed = {str(label) for label in data["labels"]}
                    for case in data["dev"] + data["holdout"]:
                        self.assertIn(str(case["label"]), allowed)

    def test_no_suite_falls_below_its_recall_floor(self):
        """Dev, holdout and, where the suite declares one, the blind split."""
        floors = json.loads((ev.EVALS / "floors.json").read_text(encoding="utf-8"))
        for name in ev.default_suites():
            result = ev.run_suite(name)
            for split in ev.SPLITS:
                if split == "blind" and not ev.SUITES[name].get("blind"):
                    continue
                with self.subTest(suite=name, split=split):
                    self.assertGreaterEqual(ev.headline(result[split]) + 1e-9, floors[name][split])

    def test_every_declared_blind_split_exists_is_scored_and_has_a_floor(self):
        """A blind floor exists exactly for the suites that declare a blind
        split, and the blind score covers every case of the named set."""
        floors = json.loads((ev.EVALS / "floors.json").read_text(encoding="utf-8"))
        for name in ev.default_suites():
            blind = ev.SUITES[name].get("blind")
            with self.subTest(suite=name):
                self.assertEqual("blind" in floors[name], bool(blind))
                if not blind:
                    continue
                data = json.loads((ev.EVALS / ev.SUITES[name]["file"]).read_text(encoding="utf-8"))
                self.assertIn(blind, data)
                result = ev.run_suite(name)
                self.assertEqual(result["blind_split"], blind)
                self.assertEqual(result["blind"]["split"], blind)
                self.assertEqual(result["blind"]["cases"], len(data[blind]))
                self.assertEqual(ev.split_label(result, "blind"), f"blind ({blind})")

    def test_the_report_page_draws_every_matrix(self):
        import score_review
        page = ev.render_html([ev.run_suite("router"), ev.run_suite("standards")], score_review.summary())
        self.assertIn("<table class=\"cm\">", page)
        self.assertIn("Rows: true label", page)
        self.assertIn("<th>Blind</th>", page)
        self.assertIn("blind (blind_v3) · 40 cases", page)
        self.assertIn("Reviewers on seeded memos", page)
        self.assertIn("Rows: the planted defect.", page)


class RecallFixTests(unittest.TestCase):
    """One example of each measured fix, so a reader sees what changed."""

    def test_a_name_alone_is_not_personal_data_when_the_values_say_otherwise(self):
        rows = [{"card_type": t, "email_opens": str(n), "full_name": f, "submitted_at": d}
                for t, n, f, d in zip(["Visa", "Amex"] * 5, range(10),
                                      ["Ali Hassan", "Sara Khan", "Omar Saeed", "Laila Noor", "John Smith",
                                       "Maria Lopez", "Fatima Zahra", "Yusuf Amin", "Chen Wei", "Priya Nair"],
                                      [f"2025-03-0{i} 10:0{i}" for i in range(1, 10)] + ["2025-03-10 11:00"])]
        flagged = {f["column"] for f in analytics.personal_data_findings(list(rows[0]), rows)}
        self.assertEqual(flagged, {"full_name"})

    def test_a_year_beside_the_date_and_a_cost_centre_are_breakdowns(self):
        text = "ship_date,year,cost_centre,cost\n" + "\n".join(
            f"2025-0{(i % 9) + 1}-1{i % 9},{2024 + i % 2},{4100 + 100 * (i % 3)},{100 + 7 * i}" for i in range(12))
        roles = mapping.suggest(*mapping.table(text))["roles"]
        self.assertEqual((roles["year"], roles["cost_centre"], roles["cost"]), ("dimension", "dimension", "measure"))

    def test_the_router_reads_naming_conventions(self):
        every = [{"provider": p} for p in ("ollama", "anthropic", "groq", "deterministic")]
        self.assertEqual(routing.provider_for("gpt-oss:20b", every), "ollama")
        self.assertEqual(routing.provider_for("llama-3.3-70b-versatile", every), "groq")
        self.assertEqual(routing.provider_for("anthropic/claude-3.7-sonnet", every), "anthropic")
        self.assertIsNone(routing.provider_for("bert-base-uncased", every))

    def test_the_raw_data_guard_knows_json_aligned_and_keyed_rows(self):
        self.assertTrue(consult.looks_like_raw_rows(json.dumps([{"sales": i} for i in range(9)])))
        self.assertTrue(consult.looks_like_raw_rows("\n".join(f"2025-0{i % 9 + 1}  North   {1000 + i}" for i in range(9))))
        self.assertTrue(consult.looks_like_raw_rows("\n".join(f"name: P{i}, salary: {9000 + i}" for i in range(9))))
        self.assertFalse(consult.looks_like_raw_rows("Revenue rose 12% to 3.4 million; costs were flat."))

    def test_jargon_abbreviations_match_only_as_words(self):
        self.assertTrue(analytics._jargon_in("The 95% CI runs from 1.2 to 3.4."))
        self.assertTrue(analytics._jargon_in("A Mann-Whitney test shows the shifts differ."))
        self.assertEqual(analytics._jargon_in("The decision was special."), [])
        self.assertEqual(analytics._jargon_in("Budget variance was 2 million."), [])

    def test_causal_wording_is_found_and_associations_are_left_alone(self):
        self.assertTrue(claims_lint.causal_phrases("Stockouts double outages."))
        self.assertTrue(claims_lint.causal_phrases("The discount increased orders by 15%."))
        self.assertTrue(claims_lint.causal_phrases("أدى نقص المخزون إلى زيادة التوقف."))
        self.assertFalse(claims_lint.causal_phrases("Orders increased 15% in weeks with a discount."))
        self.assertFalse(claims_lint.causal_phrases("Records with a stockout average twice the downtime."))
        self.assertFalse(claims_lint.causal_phrases("We cannot claim a cause from this data."))

    def test_the_round_six_constructions_are_found(self):
        """One case per class added in ADR 0056, so a rewrite cannot drop one."""
        for sentence in (
            "خفّض التدريب الجديد على التشغيل زمن التوقف غير المخطط في محطة الضخ.",
            "يعود تراجع دقة التنبؤ إلى نقص البيانات في الأشهر الأخيرة.",
            "انخفاض الحوادث جاء نتيجة تحديث نظام الإشارات.",
            "ارتفاع أسعار الوقود يدفع تكاليف النقل إلى الأعلى كل شهر.",
            "The impact of the new triage rule was a 15-minute cut in average waiting time.",
        ):
            self.assertTrue(claims_lint.causal_phrases(sentence), sentence)

    def test_a_hedge_and_a_status_are_not_claims(self):
        """Both were false positives the round-six patterns had to avoid."""
        self.assertFalse(claims_lint.causal_phrases(
            "The shift change may have contributed to the error spike, "
            "but the sample is small and we cannot confirm it."))
        self.assertFalse(claims_lint.causal_phrases(
            "The impact of the outage on customer costs is still being assessed."))
        # Arabic verb-initial reporting of a change stays out of the net.
        self.assertFalse(claims_lint.causal_phrases("زاد الإنتاج بنسبة 12% في الربع الأخير."))
        self.assertFalse(claims_lint.causal_phrases("زاد الإنتاج في الربع الأخير."))

    def test_each_standards_class_is_caught(self):
        """One case per rule in ADR 0060, so a rewrite cannot drop one."""
        import standards_lint
        for sentence in (
            "The model produces the optimal maintenance schedule.",
            "The programme saved USD 4.2 million last year.",
            "Total maintenance cost for the period was USD 50.4 million.",
            "289 high-risk assets require intervention.",
            "We recommend replacing the pumping station bearings.",
        ):
            self.assertTrue(standards_lint.refuses(sentence), sentence)

    def test_the_compliant_wording_of_each_class_passes(self):
        """The lint must not punish the sentence the standard asks for."""
        import standards_lint
        for sentence in (
            "The ranking orders assets by consequence; it is not an optimal allocation.",
            "The programme is expected to save USD 4.2 million, not yet realised.",
            "Servicing is charged to profit or loss and the overhaul is a component under IAS 16.",
            "289 high-risk observations were recorded, not 289 distinct assets.",
            "We recommend compressor 14 to protect the availability objective, owned by the depot manager.",
            "متوسط الجاهزية بلغ 96.8% خلال الفترة.",
        ):
            self.assertFalse(standards_lint.refuses(sentence), sentence)

    def test_no_pattern_carries_a_stray_control_character(self):
        """A literal backspace once stood where a word boundary was meant, and
        the pattern silently matched nothing it was written to match."""
        import standards_lint
        for pattern in (standards_lint.OPTIMISATION, standards_lint.REALISED,
                        standards_lint.CAPITALISATION, standards_lint.GRAIN,
                        standards_lint.TREATMENT, standards_lint.META,
                        standards_lint.RECOMMENDATION, standards_lint.LINE_OF_SIGHT):
            self.assertNotIn(chr(8), pattern.pattern)

    def test_the_adversarial_probe_is_labelled_as_one(self):
        """probe_v5 must never be read as a blind holdout: it was written with
        the patterns in view, so its recall is a worst case, not a measurement
        of field performance (ADR 0056)."""
        suite = json.loads((ev.EVALS / "causal.json").read_text(encoding="utf-8"))
        self.assertIn("probe_v5", suite)
        self.assertEqual(len(suite["probe_v5"]), 32)
        for case in suite["probe_v5"]:
            self.assertIn("NOT a blind holdout", case["source"])

    def test_a_blind_set_is_independent_until_it_is_used_to_fix_rules(self):
        """Blind sets were written by an agent that saw only the label definitions
        (2026-10-20 decision). While a set is still blind, none of its sentences
        may also sit in another split. Once the rules are fixed against it, it
        moves into dev, says so in every case's source, and a new blind set is
        needed to judge the fix."""
        def every_other_text(data, skip):
            return {case["text"] for key, cases in data.items()
                    if key != skip and isinstance(cases, list)
                    for case in cases if isinstance(case, dict) and "text" in case}
        for name, key, size in (("jargon", "blind_v6", 40), ("standards", "blind_v3", 40)):
            data = json.loads((ev.EVALS / f"{name}.json").read_text(encoding="utf-8"))
            if key not in data:
                continue
            with self.subTest(suite=name, set=key):
                blind = data[key]
                self.assertEqual(len(blind), size)
                self.assertEqual([c["text"] for c in blind
                                  if c["text"] in every_other_text(data, key)], [])
                for case in blind:
                    self.assertIn(case["label"], data["labels"])
                    self.assertIn("independent agent", case["source"])
                    self.assertIn("definitions only", case["source"])

    def test_blind_v6_cases_fixed_against_say_so_in_dev(self):
        """intent and causal blind_v6 were used to fix the rules on 2026-10-20."""
        for name, count in (("intent", 48), ("causal", 37)):
            data = json.loads((ev.EVALS / f"{name}.json").read_text(encoding="utf-8"))
            self.assertNotIn("blind_v6", data)
            moved = [c for c in data["dev"] if "moved into dev on 2026-10-20" in c.get("source", "")]
            self.assertEqual(len(moved), count, name)
            for case in moved:
                self.assertIn("no longer independent", case["source"])

    def test_blind_v7_cases_fixed_against_say_so_in_dev(self):
        """intent and causal blind_v7 were used to fix the rules on 2026-10-23, so
        they moved into dev and blind_v8, written independently that day, is
        the blind split, floored at its first score. No blind_v8 sentence may
        be in dev, or the blind score stops being blind. One causal case was
        set aside as a contested label and is kept, unscored, under "contested"."""
        floors = json.loads((ev.EVALS / "floors.json").read_text(encoding="utf-8"))
        for name, in_dev, contested in (("intent", 57, 0), ("causal", 49, 1)):
            with self.subTest(suite=name):
                data = json.loads((ev.EVALS / f"{name}.json").read_text(encoding="utf-8"))
                self.assertNotIn("blind_v7", data)
                self.assertEqual(ev.SUITES[name].get("blind"), "blind_v8")
                self.assertIn("blind", floors[name])
                blind_texts = {c["text"] for c in data["blind_v8"]}
                self.assertFalse(blind_texts & {c["text"] for c in data["dev"]})
                self.assertTrue(all("blind v8" in c["source"] for c in data["blind_v8"]))
                moved = [c for c in data["dev"] if "moved into dev on 2026-10-23" in c.get("source", "")]
                self.assertEqual(len(moved), in_dev)
                self.assertEqual(len(data.get("contested", [])), contested)
                for case in moved + data.get("contested", []):
                    self.assertIn("blind v7", case["source"])
                    self.assertIn("no longer independent", case["source"])
                dev_texts = {c["text"] for c in data["dev"]}
                for case in data.get("contested", []):
                    self.assertNotIn(case["text"], dev_texts)
                    self.assertIn("contested label", case["source"])

    def test_the_causal_lint_catches_the_families_blind_v6_missed(self):
        """Attribution, phrasal and Arabic origin constructions (2026-10-20)."""
        for text in ("Skipped lubrication was responsible for the gearbox breakdown.",
                     "The overrun was what brought about the pantograph failure.",
                     "Heat buckling gave rise to the speed restrictions.",
                     "Cost overruns stem from the late discovery of cracked frames.",
                     "Work orders closed late as a consequence of the planner shortage.",
                     "The cracked weld set off the chain of events.",
                     "نتج عطل الإشارة عن تسرب المياه إلى صندوق التوصيل.",
                     "كان الانحراف ناجماً عن اتساع المسافة بين القضبان.",
                     "التأخير في إغلاق أوامر العمل ناتج عن قلة المخططين.",
                     "إن نقص التزييت هو المسؤول عن انهيار علبة التروس."):
            with self.subTest(text=text):
                self.assertTrue(claims_lint.causal_phrases(text))

    def test_the_causal_lint_catches_the_families_blind_v7_missed(self):
        """Soft causal verbs, nominal origin, tracing, pseudo-clefts, a reason
        clause, and the Arabic synonyms of "led to" and "attributed to"
        (2026-10-23). Each sentence below is new, not a dev case."""
        for text in ("Poor drainage spawned the mud pumping at the level crossing.",
                     "Repeated overloads fostered fatigue cracking in the bogie frame.",
                     "The bearing failure was the direct product of a missed lubrication round.",
                     "Most door faults were traced back to a single batch of sensors.",
                     "Water ingress is what finally ruined the junction box.",
                     "Having been left uncovered, the cable drum corroded over the summer.",
                     "أفضى ضعف التخطيط إلى تأخر أعمال الصيانة.",
                     "أسفر انقطاع التيار عن توقف الخط ساعتين.",
                     "يعزو التقرير ارتفاع الأعطال إلى قدم المعدات.",
                     "نقص قطع الغيار هو ما جعل الإصلاح يتأخر."):
            with self.subTest(text=text):
                self.assertTrue(claims_lint.causal_phrases(text))

    def test_the_causal_lint_keeps_denials_tracing_and_reports_negative(self):
        """The forms that must stay negative beside the new rules: a denial, a
        figure traced to its source, a person who cannot be traced, a cleft
        that only reports, a product of numbers, and paying an amount."""
        for text in ("Nothing in the logs suggests the new pads were responsible for the noise.",
                     "There is no evidence that age drives the failures.",
                     "We make no claim about cause in this section.",
                     "Every figure can be traced back to its register.",
                     "Once rewritten, a case cannot be traced to them.",
                     "That is what happened on the night shift.",
                     "That is what we measured.",
                     "The product of the two rates is 0.4.",
                     "The induced current stayed within limits.",
                     "Bred in the depot, the team knows the fleet well.",
                     "لا يوجد ما يشير إلى أن التحديث تسبب في الأعطال.",
                     "دفع المقاول المبلغ إلى المورد."):
            with self.subTest(text=text):
                self.assertEqual(claims_lint.causal_phrases(text), [])

    def test_the_causal_lint_does_not_flag_vehicles_test_results_or_lags(self):
        """The false alarms found on the same set, and one found on the project's own docs."""
        for text in ("The driver will drive the train to the maintenance shed after the final run.",
                     "Drivers drive trams to the depot at night.",
                     "جاءت نتيجة اختبار عينة القضيب ضمن الحدود المسموحة.",
                     "The verification record was behind the tree.",
                     "Nothing was behind the reading."):
            with self.subTest(text=text):
                self.assertEqual(claims_lint.causal_phrases(text), [])
        self.assertTrue(claims_lint.causal_phrases("Rising temperatures drive the failures."))
        self.assertTrue(claims_lint.causal_phrases("جاءت نتيجة تحديث النظام."))

    def test_the_model_suite_is_opt_in_and_says_so_without_a_provider(self):
        """intent_model sends every case to a provider, so it is never part of the
        default run, the floors or the agent loop, and it reports "not available"
        rather than a score when nothing is configured."""
        self.assertNotIn("intent_model", ev.default_suites())
        self.assertIn("intent_model", ev.SUITES)

        class Unconfigured:
            def status(self):
                return {"configured": False}
        self.assertIsNone(ev._intent_model([{"text": "help", "label": "help"}], Unconfigured()))
        from server import agent_learning
        self.assertNotIn("intent_model", agent_learning.measure(["column_roles"])["suites"])

    def test_the_model_suite_scores_the_whole_assistant_through_a_scripted_provider(self):
        """What the number would mean once a real provider is configured: the model
        decides first, and the rules decide when its answer is not a valid intent."""
        answers = {"save this for me": "remember", "how is the run": "run_status",
                   "show the notes": "recall", "hello there friend": "chat"}

        class Scripted:
            def status(self):
                return {"configured": True, "provider": "scripted", "model": "fake"}

            def ask_json(self, system, user, **options):
                text = user.rsplit("Message: ", 1)[1]
                if text == "show the notes":       # an invalid answer: the rules decide
                    return "not json"
                action = answers[text]
                arguments = {"information": "the user's note"} if action == "remember" else {}
                return json.dumps({"action": action, "arguments": arguments,
                                   "reply": "Hi!" if action == "chat" else ""})
        cases = [{"text": t, "label": a} for t, a in answers.items()]
        pairs = ev._intent_model(cases, Scripted())
        self.assertEqual([p[1] for p in pairs], ["remember", "run_status", "recall", "chat"])
        # "show the notes" got an invalid answer and the rules placed it correctly;
        # the suite says how many sentences the model did not decide.
        self.assertIn("1 of 4", ev.NOTES["intent_model"])
        self.assertEqual(sum(1 for t, p, _ in pairs if t == p), 4)

    def test_the_claims_lint_cli_exits_by_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "doc.md"
            doc.write_text("Stockouts are associated with longer outages.", encoding="utf-8")
            self.assertEqual(claims_lint.main(["--doc", str(doc)]), 0)
            doc.write_text("Stockouts prolong outages.", encoding="utf-8")
            self.assertEqual(claims_lint.main(["--doc", str(doc)]), 1)

    def test_figures_in_arabic_digits_approximations_and_brackets_are_read(self):
        self.assertEqual(fc.normalise("٣٬٥٨٣٬٤٤٠ و١٢٫٤٪"), "3,583,440 و12.4%")
        self.assertEqual(fc.normalise("Variance (1,200) and margin (18.2%)"), "Variance -1,200 and margin (18.2%)")
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "doc.md"
            doc.write_text("About 6,400 hours were lost; the plan said 7,100.", encoding="utf-8")
            result = fc.check([{"label": "gap", "value": "6421"}], [doc], sourcing_only=True)
            self.assertEqual([u["number"] for u in result["unsourced"]], ["7,100"])

    def test_round_five_causal_wording(self):
        claims = lambda text: [p for p, _ in claims_lint.causal_phrases(text)]
        # Questions and untested hypotheses talk about a cause without claiming one.
        self.assertEqual(claims("Does the heat cause the breakdowns?"), [])
        self.assertEqual(claims("هل يسبب الحر زيادة الأعطال؟"), [])
        self.assertEqual(claims("The hypothesis that heat causes the breakdowns is untested."), [])
        self.assertEqual(claims("Busier depots have more delays, but we have not checked whether one drives the other."), [])
        # A hyphenated word after the verb is its object, not a preposition.
        self.assertTrue(claims("Training the dispatchers boosted on-time performance."))
        # Arabic: a longer subject inside "أدى … إلى", prefixed verbs, colloquial causatives.
        self.assertTrue(claims("أدى إلغاء الدعم عن تذاكر الطلاب إلى انخفاض عدد الركاب."))
        self.assertTrue(claims("الحر الشديد ويرفع طلبات الصيانة"))
        self.assertTrue(claims("التأخير في القطع بيخلي الأتوبيسات واقفة"))

    def test_round_five_jargon_and_intent(self):
        self.assertTrue(analytics._jargon_in("After a Bonferroni correction, two comparisons stay."))
        self.assertTrue(analytics._jargon_in("وجدنا عدم تجانس التباين في البواقي."))
        self.assertFalse(analytics._jargon_in("The residual value of the fleet is $2.1 million."))
        import assistant
        for text, action in (("Could you walk me through how to upload a spreadsheet?", "help"),
                             ("Erase our previous messages from this session, please.", "clear_history"),
                             ("pls forget that thing about the discount", "forget"),
                             ("what have you got saved about me so far", "recall"),
                             ("خلك حافظ عندك إن المورد يطلب الدفع خلال 45 يوم", "remember"),
                             ("التقرير بيقول إيه عن المصاريف؟", "explain_report")):
            with self.subTest(text=text):
                self.assertEqual(assistant.understand(text)["action"], action)

    def test_the_intent_families_blind_v7_missed(self):
        """Chat shorthand, wanting-you and what-I-told-you phrasing in Arabic,
        Gulf verbs of removing and cleaning, a started job, and named report
        sections (2026-10-23). Each sentence below is new, not a dev case."""
        import assistant
        for text, action in (("wat can u do for me", "help"),
                             ("شو اللي تقدر تسويه في بيانات الأعطال؟", "help"),
                             ("don't let me forget the audit is on Sunday", "remember"),
                             ("عايزك تفتكر إن المراجعة يوم الأحد", "remember"),
                             ("وش قلت لك عن المورد؟", "recall"),
                             ("do you still have that info about the pumps", "recall"),
                             ("ditch the note about the old supplier", "forget"),
                             ("شيل الملاحظة اللي عن المورد", "forget"),
                             ("نظّف المحادثة كلها", "clear_history"),
                             ("وقف تسجيل المحادثات من اليوم", "set_preference"),
                             ("سوّ لي تحليل على بيانات الأبواب", "start_run"),
                             ("is the analysis we kicked off this morning done", "run_status"),
                             ("the run we started an hour ago, is it stuck?", "run_status"),
                             ("quote the diagnostic section for me", "explain_report")):
            with self.subTest(text=text):
                self.assertEqual(assistant.understand(text)["action"], action)

    def test_the_new_intent_rules_keep_ordinary_sentences_as_chat(self):
        """Precision beside the new rules: a job interview, a sewing thread, a
        line's trial operation, cleaning a train, and a weekend plan."""
        import assistant
        for text in ("did the job interview finish early",
                     "reset the thread tension on the sewing machine",
                     "ايش صار في التشغيل التجريبي للخط",
                     "نظف القطار قبل الصباح",
                     "I have no idea where to begin with my weekend"):
            with self.subTest(text=text):
                self.assertEqual(assistant.understand(text)["action"], "chat")
        # Shorthand is read for the rule, but a note keeps the person's own words.
        note = assistant.understand("remember that u-bolts r due in May")
        self.assertEqual(note["arguments"]["information"], "u-bolts r due in May")

    def sourcing(self, text, register):
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "doc.md"
            doc.write_text(text, encoding="utf-8")
            return fc.check([{"label": k, "value": v} for k, v in register.items()], [doc], sourcing_only=True)

    def test_a_small_percentage_is_a_figure_and_units_must_agree(self):
        # Benchmark A: "27%" was skipped as a small count, and "40%" passed
        # because the register held $39.95.
        result = self.sourcing("Online orders grew 27%. Sales rose 40%. Store 17 opened.", {"Basket": "$39.95"})
        self.assertEqual(sorted(u["number"] for u in result["unsourced"]), ["27%", "40%"])

    def test_a_figure_its_sentence_derives_is_sourced_and_a_slip_is_wrong(self):
        register = {"Revenue 2025": "$12,480,000", "Revenue 2024": "$11,200,000", "Stores": "48", "Staff": "610"}
        text = ("Revenue reached $12.48 million in 2025, up from $11.2 million in 2024. That is growth of 13.4%. "
                "With 610 staff across 48 stores, each store has 15.2 staff on average. "
                "Revenue per store was about $260,000.")
        result = self.sourcing(text, register)
        self.assertEqual(result["unsourced"], [])
        wrong = {w["result"]: w["computed"] for w in result["wrong_arithmetic"]}
        self.assertEqual(set(wrong), {"13.4%", "15.2"})
        self.assertAlmostEqual(wrong["13.4%"], 11.428571, places=4)
        self.assertAlmostEqual(wrong["15.2"], 12.708333, places=4)

    def test_a_fall_written_as_a_positive_size_is_read_as_the_fall(self):
        # Benchmark D showed "fell from 468 to 412, a fall of 12.0%" flagged as
        # 56 / 412: a fall computes negative, prose writes its size. These
        # sentences are new, so D stays held out for the checker.
        register = {"Lift faults 2024": "250", "Lift faults 2025": "200", "Lift fault change": "-20.0%",
                    "Escalator stoppages 2024": "160", "Escalator stoppages 2025": "136",
                    "Door faults 2024": "80", "Door faults 2025": "60"}
        text = ("Lift faults fell from 250 in 2024 to 200 in 2025, 50 fewer or a fall of 20.0%. "
                "Escalator stoppages dropped from 160 to 136, a reduction of 24 or 15.0%. "
                "Door faults declined from 80 to 60, a reduction of 30.0%.")
        result = self.sourcing(text, register)
        self.assertEqual(result["unsourced"], [])
        wrong = {w["result"]: w["computed"] for w in result["wrong_arithmetic"]}
        # The real slip is still caught, against the right base: 20 / 80.
        self.assertEqual(set(wrong), {"30.0%"})
        self.assertAlmostEqual(abs(wrong["30.0%"]), 25.0, places=4)

    def test_euro_pound_and_dirham_amounts_are_read_like_dollars(self):
        # Benchmark E showed "€310" and "€1,150" reported as unsourced although
        # the register held them: only "$" was read as money. Fresh figures.
        register = {"Pump seal": "€420", "Hoist service": "£2,750", "Lift contract": "AED 96,000",
                    "Escalator contract": "48,500 AED", "Fan belt": "د.إ 380"}
        text = ("A pump seal costs €420 and a hoist service £2,750. The lift contract is AED 96,000, "
                "the escalator contract 48,500 AED and a fan belt د.إ 380. A spare motor costs €9,900.")
        result = self.sourcing(text, register)
        self.assertEqual([u["number"] for u in result["unsourced"]], ["$9,900"])

    def test_a_figure_is_not_found_inside_a_longer_number_or_a_clock_time(self):
        # Memo F: coverage reported a missing 4.9 as "05" from "05:00", and a
        # count of 5 as found in "5.2". A missing figure must read as missing.
        text = "Shift handover runs from 06:00 to 07:30. Mean delay was 3.8 minutes over 1,240.5 km."
        numbers = fc.numbers_in(text, keep_small=True)
        self.assertNotIn("06", numbers)
        self.assertNotIn("00", numbers)
        for value in ("6", "7", "3", "1,240", "7.4"):
            self.assertIsNone(fc.found_in(text, value, numbers), value)
        for value in ("3.8", "1,240.5"):
            self.assertIsNotNone(fc.found_in(text, value, numbers), value)
        self.assertIsNotNone(fc.found_in("a wait of 4.0 hours", "4"))  # the same figure

    def test_a_change_in_percentage_points_is_the_difference_of_the_percentages(self):
        # Benchmark D: "fell from 40.9% to 37.5%, a decline of 8.3 percentage
        # points" was reported as an unsourced 8.3, when 8.3 is the relative
        # change written as points. Fresh sentences, so D stays held out.
        register = {"On-time 2024": "88.0%", "On-time 2025": "92.4%", "Rework 2024": "12.5%", "Rework 2025": "10.0%",
                    "Uptime 2024": "97.20%", "Uptime 2025": "97.65%"}
        text = ("On-time completion rose from 88.0% to 92.4%, a gain of 4.4 percentage points. "
                "Rework fell from 12.5% to 10.0%, a drop of 20.0 percentage points. "
                "Uptime improved from 97.20% to 97.65%, up 0.45 points.")
        result = self.sourcing(text, register)
        self.assertEqual(result["unsourced"], [])
        wrong = {w["result"]: w["computed"] for w in result["wrong_arithmetic"]}
        # 20.0 is the relative fall (2.5 / 12.5); in points it is 2.5.
        self.assertEqual(set(wrong), {"20.0"})
        self.assertAlmostEqual(wrong["20.0"], 2.5, places=4)

    def test_a_table_read_as_one_sentence_derives_nothing(self):
        # A dashboard's data table: dozens of figures and the word "per"; any
        # two of them would "derive" a third, so the rule keeps to prose.
        months = " ".join(f"2024-{m:02d} {7_000_000 + m * 104_729:,}" for m in range(1, 13))
        text = f"Loss per record by month. The numbers in this chart Label Value {months} Total 7,104,729"
        result = self.sourcing(text, {"January": "7,104,729", "February": "7,209,458"})
        self.assertEqual(result["wrong_arithmetic"], [])
        self.assertEqual(len(result["unsourced"]), 10)

    def test_counts_written_in_english_words_are_read(self):
        # Memo F: coverage reported "five" interchange stations and "two"
        # rectifiers as missing. Fresh sentences, so F stays held out.
        text = ("The depot has seven hoists, twenty-four wheel lathes, two hundred and fifty bogies, "
                "a thousand spare bolts and forty two cranes. Two million dirhams were spent.")
        expected = {"seven": 7, "twenty-four": 24, "two hundred and fifty": 250, "a thousand": 1000,
                    "forty two": 42, "Two million": 2_000_000}
        self.assertEqual({p: fc.value_of(p) for p, _, _ in fc.word_figures(text)}, expected)
        numbers = fc.numbers_in(text, keep_small=True)
        for value in ("7", "24", "250", "1,000", "42", "2,000,000"):
            self.assertIn("(in words)", fc.found_in(text, value, numbers) or "", value)
        # A count in words is whole: "seven" is not a rounded 6.8.
        self.assertIsNone(fc.found_in(text, "6.8", numbers))
        # Small counts in words are labels in the sourcing pass, as digits are;
        # a larger figure in words must be sourced like any other.
        result = self.sourcing(text, {"Bogies": "250", "Spend": "2,000,000"})
        self.assertEqual(sorted(u["number"] for u in result["unsourced"]), ["a thousand", "forty two"])

    def test_number_words_that_are_not_counts_are_left_alone(self):
        text = ("One of the fans failed. It was a one-off. No one was hurt, and the new one is fitted. "
                "One in five trains ran late. Two-thirds of the staff work the second shift for "
                "hundreds of hours on a three-phase supply.")
        self.assertEqual([p for p, _, _ in fc.word_figures(text)], ["three"])
        for value in ("1", "5", "2"):
            self.assertIsNone(fc.found_in(text, value), value)

    def test_counts_written_in_arabic_words_are_read(self):
        text = ("في المستودع خمس محطات وخمسة وعشرون مصعدا وثلاثمئة مضخة واثنتا عشرة رافعة. "
                "بلغت ساعات العمل ثلاثة آلاف ساعة، وكلفت الصيانة ألفا وخمسمئة. ومئة وعشرون مروحة.")
        found = {fc._ar(p): v for p, v, _ in fc.word_figures(text)}
        self.assertEqual(sorted(found.values()), [5, 12, 25, 120, 300, 1500, 3000])
        numbers = fc.numbers_in(text, keep_small=True)
        for value in ("5", "25", "300", "12", "3,000", "1,500", "120"):
            self.assertIn("(in words)", fc.found_in(text, value, numbers) or "", value)
        # Feminine and masculine forms, and the two spellings of a hundred, are one number.
        for phrase, value in (("ثلاث", 3), ("ثلاثة", 3), ("مائة", 100), ("مئة", 100), ("إحدى عشرة", 11),
                              ("أربعون", 40), ("تسعين", 90), ("ألف", 1000)):
            self.assertEqual(fc.value_of(phrase), value, phrase)
        # A short feminine form before a definite noun is a fraction: "خمس السكان" is a fifth.
        self.assertEqual(fc.word_figures("يسكن خمس السكان في المدينة، وكل واحد منهم يعمل."), [])

    def test_a_register_in_millions_sources_figures_written_in_millions(self):
        # Memo G: the register held "Train-km 2025 (million)" as 1.84, and the
        # memo wrote "1.84 million", which was read as 1,840,000 and reported
        # unsourced. A label that names its scale is that scale. Fresh text.
        text = "Spend was 9.6 million dirhams and the fleet ran 2.05 million km."
        result = self.sourcing(text, {"Spend (million AED)": "9.6", "Fleet km 2025 (million)": "2.05"})
        self.assertEqual(result["unsourced"], [])
        # Without a scale in the label, 2.05 is 2.05, and "2.05 million" is not it.
        result = self.sourcing(text, {"Spend (million AED)": "9.6", "Fleet km 2025": "2.05"})
        self.assertEqual([u["number"] for u in result["unsourced"]], ["2.05 million"])

    def test_one_figure_written_twice_is_not_two_inputs(self):
        # 75.2% and 0.752 are one quantity: their difference must not source 74.1%.
        result = self.sourcing("The preventive ratio was 75.2%, up from 74.1%.", {"Preventive ratio": "0.752"})
        self.assertEqual([u["number"] for u in result["unsourced"]], ["74.1%"])


class ReviewerBenchmarkTests(unittest.TestCase):
    """The seeded memos in evals/reviewers/ and their scorer (ADR 0027)."""

    def test_every_benchmark_labels_paragraphs_that_exist(self):
        import re
        for bench in ("A", "B", "C", "D", "E", "F"):
            with self.subTest(bench=bench):
                folder = ROOT / "evals" / "reviewers" / bench
                labels = json.loads((folder / "labels.json").read_text(encoding="utf-8"))
                memo = (folder / "memo.md").read_text(encoding="utf-8")
                self.assertEqual(re.findall(r"\[(P\d{2})\]", memo), labels["paragraphs"])
                self.assertLessEqual(set(labels["defects"]), set(labels["paragraphs"]))
                for categories in labels["defects"].values():
                    self.assertLessEqual(set(categories), set(labels["categories"]))
                self.assertTrue(fc.load_register(folder / "register.csv", "Expected", ["Check"]))

    def test_the_three_lane_benchmarks_label_paragraphs_that_exist(self):
        """Memos H, I and J (assessment G9) have no register: their lanes
        are compliance, security and accessibility, not figures."""
        import re
        import score_review
        lanes = {"H": "brief-compliance-reviewer", "I": "security-privacy-reviewer",
                 "J": "accessibility-i18n-reviewer"}
        for bench, agent in lanes.items():
            with self.subTest(bench=bench):
                folder = ROOT / "evals" / "reviewers" / bench
                labels = json.loads((folder / "labels.json").read_text(encoding="utf-8"))
                memo = (folder / "memo.md").read_text(encoding="utf-8")
                self.assertEqual(re.findall(r"\[(P\d{2})\]", memo), labels["paragraphs"])
                self.assertLessEqual(set(labels["defects"]), set(labels["paragraphs"]))
                self.assertEqual(set(labels["categories"]), set(score_review.LANES[agent]))
                self.assertFalse(set(labels["decoys"]) & set(labels["defects"]))
                self.assertEqual(set(labels["why"]), set(labels["defects"]))
                for categories in labels["defects"].values():
                    self.assertLessEqual(set(categories), set(labels["categories"]))
        self.assertTrue((ROOT / "evals" / "reviewers" / "H" / "brief.md").exists())

    def test_the_benchmarked_reviewers_keep_their_recorded_floors(self):
        """The saved first runs of the three reviewers (G9) score at or
        above the floors recorded from them; a later run is saved beside
        the first, never over it."""
        import score_review
        floors = json.loads((ROOT / "evals" / "floors.json").read_text(encoding="utf-8"))
        for key, agent in (("brief_compliance_reviewer", "brief-compliance-reviewer"),
                           ("security_privacy_reviewer", "security-privacy-reviewer"),
                           ("accessibility_i18n_reviewer", "accessibility-i18n-reviewer")):
            for bench, floor in floors[key].items():
                with self.subTest(agent=agent, bench=bench):
                    run = ROOT / "evals" / "reviewers" / "runs" / f"{agent}-{bench}-named-v1.txt"
                    result = score_review.score(ROOT / "evals" / "reviewers" / bench,
                                                run.read_text(encoding="utf-8"), score_review.LANES[agent])
                    self.assertGreaterEqual(result["detection"]["recall"] + 1e-9, floor["detection"])
                    self.assertGreaterEqual(result["recall"] + 1e-9, floor["lane"])
                    self.assertLessEqual(len(result["false_alarms"]), floor["false_alarms"])

    def test_the_scorer_separates_misses_false_alarms_and_secondary_findings(self):
        import score_review
        reply = ("FINDING F1 · major · P02\nCategory: arithmetic\n\n"
                 "FINDING F2 · major · P07\nCategory: causal_claim\n\n"
                 "FINDING F3 · minor · P08\nCategory: denominator\n\n"
                 "FINDING F4 · major · P06\nCategory: unsourced_figure\n\n"
                 "FINDING F5 · major · P06\nCategory: denominator\n")
        result = score_review.score(ROOT / "evals" / "reviewers" / "A", reply, ["causal_claim", "denominator", "overclaim"])
        self.assertEqual(result["false_alarms"], ["P08 · denominator"])
        self.assertIn("P06 · unsourced_figure", result["secondary"])
        self.assertEqual(result["category_confusion"]["matrix"]["overclaim"]["causal_claim"], 1)
        self.assertEqual(result["category_confusion"]["matrix"]["overclaim"]["missed"], 1)
        self.assertEqual(result["per_category"]["denominator"]["misses"], ["P15 · denominator"])
        self.assertAlmostEqual(result["recall"], 1 / 6)

    def test_the_checker_as_a_reviewer_keeps_its_benchmark_recall(self):
        import score_review
        floors = json.loads((ROOT / "evals" / "floors.json").read_text(encoding="utf-8"))["figures_tool"]
        for bench, floor in floors.items():
            with self.subTest(bench=bench):
                result = score_review.score(ROOT / "evals" / "reviewers" / bench,
                                            score_review.figures_tool_findings(ROOT / "evals" / "reviewers" / bench),
                                            ["unsourced_figure", "arithmetic"])
                self.assertGreaterEqual(result["detection"]["recall"] + 1e-9, floor)
                self.assertEqual(result["false_alarms"], [])


if __name__ == "__main__":
    unittest.main()

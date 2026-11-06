## 12. Pilot roadmap, KPIs and decision rules
<!-- kb: domain=mba.9227.g02.pilot; limits=academic_case|not_rmd_operational_rule -->


### 12.1 Roadmap

| Period | Proposed work in the G02 case |
|---|---|
| Weeks 1 to 3 | Partner selection and initial preparation |
| Weeks 1 to 6 | Data/legal review, templates, platform/feed configuration, rule recalibration and training |
| Weeks 7 to 18 | Twelve-week pilot in RJ, BA and CE, five service agents, weekly KPI review |
| Week 12 | Roadmap midpoint check |
| Weeks 19 to 20 | Management comparison of measured results and decision |
| Week 21 onward | Scale, scale with carrier tracking, modify/re-pilot or stop with lessons recorded |

Source: S05, slides 20 to 22. This is a proposal; no completed rollout is established.

### 12.2 Four checkpoint measures

| Measure | Historical baseline | Proposed pilot criterion |
|---|---|---|
| Low reviews among reviewed late orders | 70.2% in pilot states; 62.4% network | At least 10 percentage points below comparison |
| Late-delivery rate | 12.2% in pilot states; 6.8% network | At least 1.5 percentage points below comparison |
| Alerts handled in the stated time | New measure | At least 90% handled within 24 hours |
| Late orders flagged in advance | 25.4% in pilot states; 33.8% network | 40% is the proposed detection decision threshold |

These are academic proposed criteria requiring management acceptance in that case. They are not observed benefits or approved RMD service levels. [S05, slides 7, 8]

### 12.3 Decision table reported in the presentation

“Improvement” means measure 1 and/or measure 2 meets its target. “Workload met” refers to the alert-handling criterion.

| Improvement | Workload criterion | Detection | Proposed decision |
|---|---|---|---|
| Yes | Met | At least 40% | Scale |
| Yes | Met | Below 40% | Scale and add carrier data |
| Yes | Not met | Any | Modify rule or staffing |
| No | Any | Below 40% | Modify, add carrier data and re-pilot |
| No | Any | At least 40% | Stop |

The deck presents this as a mutually exclusive rule. Before real use, define the measurement population, comparison design, uncertainty, acceptable adverse effects and who applies the rule. Threshold crossing alone is not proof of economic value.

### 12.4 Important interpretation limits

- A lower late-order count can leave a more severe set of late orders. Their review score may worsen even when the intervention prevents some delays.
- The deck reports approximate measurement limits of ±7 percentage points for the review measure and ±1.7 points for the late-rate measure. Their statistical assumptions were not reproduced here.
- A 1.5-point target near a reported 1.7-point uncertainty scale may be difficult to distinguish reliably. Record uncertainty and sample-size assumptions before interpreting success or failure.
- The statement that “scale plus carrier data” is the most likely outcome is an expectation in the deck, not a result established by the backtest.
- The absence of causal intervention data prevents a claim that messaging, seller chasing or shipping upgrades will achieve the targets.

### 12.5 Preconditions and risk controls

The deck lists management acceptance of targets and decision rules, DPO review, partner and licence arrangements, recalibration on current data, an agreed shipping-upgrade cap, and parallel AfterShip due diligence. [S05, slide 25]

Main project risks are poor detection, outdated thresholds, inaccurate AI messages, data handling, alert workload and intervention cost. Proposed mitigations include recalibration, bounded inputs, templates, human approval, controlled access, training and cost monitoring. [S05, slide 22]

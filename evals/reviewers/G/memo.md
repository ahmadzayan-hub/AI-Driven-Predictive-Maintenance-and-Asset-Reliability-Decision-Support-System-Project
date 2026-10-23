# Corrin Valley Tramway: 2025 Infrastructure Reliability and Maintenance Year-End Review (synthetic benchmark G)

[P01] This review covers the fixed infrastructure of the fictional Corrin Valley Tramway for calendar year 2025: 21.6 km of mainline double track and 2.4 km of depot track (24.0 km in total), 31 stops, 148 switches and crossings (112 on the mainline and 36 in the depot), 9 traction substations, the overhead contact system, signalling and interlocking, depot plant and the passenger information system (PIS). Passenger service runs 18 hours a day, so the required service time for the year was 6,570 hours out of 8,760 calendar hours. All figures are synthetic.

[P02] The maintenance management system recorded 4,210 completed work orders in 2025: 2,940 preventive and 1,270 corrective. Of the 3,100 preventive work orders scheduled, 2,940 were completed, a preventive compliance of 94.8%.

[P03] Signalling-attributed delay incidents fell from 52 in 2024 to 46 in 2025. Service volume also changed, from 1.79 million train-km to 1.84 million train-km, so we normalise by service delivered: the rate fell from 29.1 to 25.0 incidents per million train-km.

[P04] Switch failures totalled 39 in 2025: 30 on the mainline and 9 in the depot. Spread over the track they serve, the mainline recorded 1.39 failures per track-km (30 over 21.6 km) and the depot 3.75 failures per track-km (9 over 2.4 km). Depot switches are therefore 2.7 times less reliable than mainline switches, and we propose moving the depot switch inspection from quarterly to monthly.

[P05] Eighteen of the 148 point machines failed during the year. Those 18 machines had accumulated 81,000 operating hours between them when they failed, giving a point machine MTBF of 4,500 hours (81,000 divided by 18), or a failure roughly every six months per machine. We will therefore introduce a fixed overhaul of every point machine at 4,000 operating hours, ahead of the expected failure.

[P06] Axle counter heads provide a useful comparison. All 60 heads were in service for the full year, giving 525,600 head-hours of exposure, which includes the 48 heads that did not fail; the 12 failed heads were replaced within the shift. The MTBF is 525,600 divided by 12, or 43,800 hours.

[P07] Insulated rail joints recorded 22 failures, 14 of them (64%) within 90 days of installation. A Weibull fit to the failure ages gives a shape parameter of 0.6, which confirms that the joints are wearing out in service. We will shorten the planned replacement interval for insulated rail joints from 10 years to 6 years.

[P08] Switch clamp-lock assemblies show the opposite pattern. A Weibull fit gives a shape parameter of 3.4 with a characteristic life of 7.5 years, and all 9 failures in 2025 were in assemblies older than 6.5 years. Age-based replacement at 6 years is retained because the hazard rate rises steeply with age.

[P09] PIS display controller boards recorded 41 failures among 310 boards. A Weibull fit gives a shape parameter of 1.0 (confidence range 0.98 to 1.04) and failures show no relationship with board age. We propose replacing all 310 boards every 3 years at 1,200 UA each, a cost of 372,000 UA per cycle, so that boards are renewed before they fail and controller failures fall.

[P10] Traction power availability is measured, as the operating contract requires, over required service time. Supply was lost for 19.71 hours during service hours, giving an availability of 99.70% (6,550.29 of 6,570 hours). Isolations taken in the overnight engineering window are planned and are correctly excluded.

[P11] The PIS availability target of 95.0% is also defined over required service time. The system was unavailable for 438 hours in 2025, all of them within service hours. Over the 8,760 hours in the year this gives an availability of 95.0% (1 minus 438 divided by 8,760), so the PIS target was met.

[P12] Overhead contact wire wear is measured once every 12 months by the measurement trolley. On the high-wear curve sections the P-F interval, from detectable thinning to strand failure, is estimated at 4 months. We will keep the 12-month measurement cycle, which saves 2 track possessions per year compared with a 6-month cycle.

[P13] Rail head rolling contact fatigue is inspected by eddy current every 3 months. The P-F interval from a detectable crack to a reportable defect is estimated at 9 months, so each crack has three inspection opportunities before it becomes reportable.

[P14] No broken rails occurred in 2025, against 3 in 2024. The enhanced ultrasonic rail testing programme introduced in January has eliminated broken-rail risk on the network.

[P15] Substation S4 has two rectifiers, each with an unavailability of 0.02. Both are fed from the same 11 kV incomer cable and share one cooling fan unit. Treating the pair as independent, the probability that both are unavailable together is 0.02 multiplied by 0.02, or 0.0004, so S4 rectification is available 99.96% of the time and no further resilience work is needed.

[P16] The interlocking is supplied by two uninterruptible power supply units on separate feeders in separate equipment rooms, each with an unavailability of 0.01. The independent term is 0.0001 (0.01 multiplied by 0.01) and a common-cause beta factor of 0.05 adds 0.0005 (0.05 multiplied by 0.01), so the combined unavailability is 0.0006.

[P17] The mean time to repair for mainline switch failures was 1.5 hours, measured from the technician's arrival on site to the completion of the work order. Each switch failure therefore costs 1.5 hours of service disruption, and the 30 mainline switch failures cost 45 service-hours in 2025.

[P18] The depot wheel lathe failed 4 times. Its mean downtime per failure was 18 hours: 6 hours of active repair, 10 hours waiting for spares and 2 hours for access and isolation. The 72 hours of downtime over its 4,000 scheduled operating hours (two 8-hour shifts on 250 days) give an availability of 98.2%.

[P19] Route setting depends on three subsystems in series: the interlocking (reliability 0.98 over the reference mission), the object controllers (0.96) and trackside train detection (0.97). The average route-setting reliability is therefore 0.97 ((0.98 plus 0.96 plus 0.97) divided by 3), which meets the 0.95 target.

[P20] The PIS message chain also runs in series: the central server (reliability 0.99), the communications network (0.98) and the stop display (0.97). Multiplying the three gives a chain reliability of 0.941, or 94.1%.

[P21] The depot workshop has 420 LED high-bay light fittings, of which 11 failed in 2025. Their failure is immediately evident, the fittings overlap so a single failure leaves the bay adequately lit, they have no safety function (emergency lighting is a separate, tested system) and replacement takes under an hour. These fittings are managed as run-to-failure.

[P22] Each of the 31 stops has two passenger emergency help points, 62 units in total. Each unit costs 380 UA and only 3 failed in 2025, so from 2026 the help points will move to run-to-failure and the monthly functional test will be withdrawn.

[P23] New track drainage was installed at 9 stops due for resurfacing in 2025. Those stops recorded 4 track geometry faults, against 15 at 9 other stops without new drainage. The new drainage caused a 73% reduction in track geometry faults.

[P24] Splitting the 112 mainline switches at the median of daily movements, the 56 high-traffic switches recorded 21 failures and the 56 low-traffic switches 9, a failure rate 2.3 times higher. This is an association only: the high-traffic switches are also older on average, so we cannot attribute the difference to traffic. A matched comparison by age is planned for 2026.

[P25] Asset criticality is ranked by risk, combining the safety, service and cost consequences of failure with failure frequency, rather than by repair cost alone. On this basis switch heaters (repair cost 9,500 UA) rank above the depot wash plant (repair cost 48,000 UA), because a heater failure in frost can stop the service and the wash plant can be bypassed for days.

[P26] Infrastructure maintenance spend in 2025 was 14.6 million UA: track 4.1 million, switches and crossings 2.3 million, power and overhead line 3.4 million, signalling and interlocking 2.7 million, depot plant 1.2 million and passenger information 0.9 million.

[P27] Priorities for 2026 are the switch heater renewal on the exposed northern section, a review of spares holding for depot plant, and the planned age-matched switch traffic study.

[P28] This memo is a draft for review by the Head of Infrastructure Maintenance. No interval change, run-to-failure decision or budget change takes effect until it is approved by a person with recorded authority.

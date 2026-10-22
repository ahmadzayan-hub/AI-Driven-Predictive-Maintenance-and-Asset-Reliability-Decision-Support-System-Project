package com.assetreliability.core.decision

import com.assetreliability.core.api.ApiJson
import com.assetreliability.core.api.ExecutiveBrief
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class DecisionSupportTest {
    private val brief: ExecutiveBrief =
        ApiJson.decodeFromString(javaClass.getResource("/executive-demo.json")!!.readText())

    @Test
    fun `the command centre lifts every tile from the brief and computes nothing`() {
        val centre = DecisionSupport.from(brief)
        assertEquals("5fe5d44a8391", centre.runId)
        assertTrue(centre.recommendation.startsWith("Endorse a scoped"))
        assertEquals("limited", centre.readiness)
        assertEquals(240, centre.records)
        assertEquals(7, centre.measureCount)
        assertEquals(4, centre.decisions.size)
        assertEquals("Maintenance planner", centre.decisions[0].owner)
        assertEquals(4, centre.unavailableMeasures)
        assertEquals(2, centre.models.size)
        assertEquals(Tone.UNASSESSED, centre.models[0].tone)
        assertEquals(Tone.GOOD, centre.models[1].tone)
        assertTrue(centre.recommendedAction!!.startsWith("Recommended action"))
        assertTrue(centre.assumption!!.contains("10%"))
        assertTrue(centre.dataQuality!!.startsWith("Data quality scores 100.0"))
        assertEquals(4, centre.failedChecks)
        assertEquals(5, centre.limitations.size)
        assertEquals(3, centre.questions.size)
    }

    @Test
    fun `measures with a verdict come first then one of each family never more than six`() {
        val picked = DecisionSupport.pickMeasures(brief.kpis.measures).map { it.key }
        assertEquals("first_time_fix", picked[0])
        assertTrue(picked.containsAll(listOf("availability", "preventive_share", "loss_per_record")))
        assertEquals(6, picked.size)
        val tiles = DecisionSupport.from(brief).measures
        assertEquals("75.8%", tiles[0].value)
        assertEquals(Tone.GOOD, tiles[0].tone)
        assertEquals("At or above the target of 70%.", tiles[0].reason)
        val unassessed = tiles.first { it.key == "availability" }
        assertEquals(Tone.UNASSESSED, unassessed.tone)
        assertNull(unassessed.reason)
    }

    @Test
    fun `figures keep their scale and western digits in arabic`() {
        val money = brief.kpis.measures.first { it.key == "loss_per_record" }
        assertEquals("4,332.03", KpiFormat.format(money, "en"))
        assertEquals("4,332.03", KpiFormat.format(money, "ar"))
        assertEquals("source currency", KpiFormat.unit(money, "en"))
        assertEquals("عملة المصدر", KpiFormat.unit(money, "ar"))
        val ratio = brief.kpis.measures.first { it.key == "loss_to_maintenance_ratio" }
        assertEquals("2.2×", KpiFormat.format(ratio))
        val hours = brief.kpis.measures.first { it.key == "downtime_per_record" }
        assertEquals("16.7", KpiFormat.format(hours))
        assertEquals("h", KpiFormat.unit(hours))
        val undefined = brief.kpis.measures.last()
        assertNull(KpiFormat.format(undefined))
        assertEquals(Tone.UNAVAILABLE, toneOf(undefined))
    }

    @Test
    fun `without an advisory the priorities are the decisions and the headline is the recommendation`() {
        val plain = brief.copy(advisory = null)
        val centre = DecisionSupport.from(plain)
        assertEquals(brief.headline, centre.recommendation)
        assertEquals(listOf("overdue_share"), centre.decisions.map { it.id })
        assertEquals("", centre.decisions[0].owner)
        assertNull(centre.prediction)
    }
}

package com.assetreliability.core.decision

import com.assetreliability.core.api.ExecutiveBrief
import com.assetreliability.core.api.KpiMeasure
import com.assetreliability.core.api.ModelCard
import kotlinx.serialization.json.JsonPrimitive
import java.math.RoundingMode
import java.text.NumberFormat
import java.util.Locale

/** One reading of a verdict for every screen. Only a supplied assessment
 *  establishes performance; sign and magnitude never do. */
enum class Tone { GOOD, OKAY, BAD, UNASSESSED, UNAVAILABLE }

fun toneOf(measure: KpiMeasure): Tone {
    val value = measure.value
    if (value == null || value.isNaN() || value.isInfinite()) return Tone.UNAVAILABLE
    return when (measure.assessment?.status) {
        "good" -> Tone.GOOD
        "okay" -> Tone.OKAY
        "bad" -> Tone.BAD
        "unavailable" -> Tone.UNAVAILABLE
        else -> Tone.UNASSESSED
    }
}

/** The same rule as the web's `shared/modelTone.ts`. */
fun toneOf(model: ModelCard): Tone {
    val verdict = (model.details["verdict"] as? JsonPrimitive)?.content
    if (model.fitted == false || model.metric == null || verdict == "not_supported") return Tone.UNASSESSED
    if (verdict == "weak" || model.beatsBaseline == false) return Tone.BAD
    return if (model.beatsBaseline == true) Tone.GOOD else Tone.UNASSESSED
}

/** A figure on its own scale, Western digits in Arabic too (ADR 0018). */
object KpiFormat {
    fun format(measure: KpiMeasure, language: String = "en"): String? {
        val value = measure.value ?: return null
        if (value.isNaN() || value.isInfinite()) return null
        val locale = if (language == "ar") Locale.forLanguageTag("ar-u-nu-latn") else Locale.UK
        val digits = if (measure.scale == "money") 2 else 1
        // Rounded on the shortest decimal form of the value, half up, which
        // is how the browser's Intl formatting rounds: 4332.025 prints as
        // 4,332.03 on the phone as on the web, not 4,332.02 from the binary.
        val rounded = java.math.BigDecimal(value.toString()).setScale(digits, RoundingMode.HALF_UP)
        val number = NumberFormat.getNumberInstance(locale).apply {
            minimumFractionDigits = digits
            maximumFractionDigits = digits
        }.format(rounded)
        return when (measure.scale) {
            "percent" -> "$number%"
            "ratio" -> "$number×"
            else -> number
        }
    }

    /** The unit a reader needs beside the number; money has no currency
     *  until the dataset states one (assessment finding U4). */
    fun unit(measure: KpiMeasure, language: String = "en"): String = when (measure.scale) {
        "hours" -> if (language == "ar") "ساعة" else "h"
        "money" -> if (language == "ar") "عملة المصدر" else "source currency"
        else -> ""
    }
}

data class DecisionItem(val id: String, val title: String, val detail: String, val owner: String, val gate: String)
data class MeasureTile(val key: String, val title: String, val value: String?, val unit: String, val tone: Tone, val reason: String?)
data class ModelTile(val target: String, val tone: Tone, val reason: String?)

/** The brief, arranged for a decision-maker. Nothing here is computed from
 *  rows: every field is lifted from the server's brief. */
data class CommandCentre(
    val runId: String,
    val datasetName: String,
    val asOf: String?,
    val recommendation: String,
    val readiness: String,
    val records: Int,
    val measureCount: Int,
    val decisions: List<DecisionItem>,
    val measures: List<MeasureTile>,
    val unavailableMeasures: Int,
    val models: List<ModelTile>,
    val prediction: String?,
    val recommendedAction: String?,
    val assumption: String?,
    val dataQuality: String?,
    val failedChecks: Int,
    val limitations: List<String>,
    val questions: List<String>,
)

object DecisionSupport {
    private const val MAX_KPIS = 6
    private val FAMILY_ORDER = listOf("reliability", "execution", "cost")

    /** Every measure with a verdict first, then the first of each family,
     *  never more than six: the web Command Centre's rule. */
    fun pickMeasures(measures: List<KpiMeasure>): List<KpiMeasure> {
        val chosen = measures.filter { it.assessment?.status in setOf("good", "okay", "bad") }.toMutableList()
        for (family in FAMILY_ORDER) {
            measures.firstOrNull { it.family == family && it !in chosen }?.let { chosen.add(it) }
        }
        for (measure in measures) {
            if (chosen.size >= MAX_KPIS) break
            if (measure !in chosen) chosen.add(measure)
        }
        return chosen.take(MAX_KPIS)
    }

    fun from(brief: ExecutiveBrief, language: String = "en"): CommandCentre {
        val decisions = brief.advisory?.decisions?.takeIf { it.isNotEmpty() }
            ?.map { DecisionItem(it.id, it.title, it.action, it.owner, it.gate) }
            ?: brief.priorities.map { DecisionItem(it.id, it.title, it.detail, "", "") }
        val measures = pickMeasures(brief.kpis.measures).map { m ->
            val tone = toneOf(m)
            val verdict = tone == Tone.GOOD || tone == Tone.OKAY || tone == Tone.BAD
            MeasureTile(m.key, m.title, KpiFormat.format(m, language), KpiFormat.unit(m, language), tone,
                if (verdict) m.assessment?.reason else null)
        }
        val models = brief.models.take(4).map { card ->
            ModelTile(card.target, toneOf(card), (card.details["reason"] as? JsonPrimitive)?.content)
        }
        val failedChecks = brief.evidence.firstOrNull { it.id == "executive.validation.failed_checks" }
            ?.value?.toInt() ?: 0
        return CommandCentre(
            runId = brief.run.id,
            datasetName = brief.run.datasetName,
            asOf = brief.run.updatedAt,
            recommendation = brief.advisory?.recommendation?.takeIf { it.isNotBlank() } ?: brief.headline,
            readiness = brief.readiness.status,
            records = brief.scope.records,
            measureCount = brief.kpis.measures.size,
            decisions = decisions.take(4),
            measures = measures,
            unavailableMeasures = brief.kpis.unavailable.size,
            models = models,
            prediction = brief.advisory?.prediction?.takeIf { it.isNotBlank() },
            recommendedAction = brief.findings.firstOrNull { it.kind == "recommendation" }?.text,
            assumption = brief.findings.firstOrNull { it.stage == "prescriptive" && it.kind == "assumption" }?.text,
            dataQuality = brief.findings.firstOrNull { it.stage == "quality" }?.text,
            failedChecks = failedChecks,
            limitations = brief.readiness.limitations,
            questions = brief.questions.take(3).map { it.text },
        )
    }
}

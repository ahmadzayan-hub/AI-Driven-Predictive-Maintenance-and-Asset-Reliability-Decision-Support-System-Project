package com.assetreliability.app.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.slideInVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.assetreliability.app.ui.t
import com.assetreliability.app.ui.theme.Tokens
import com.assetreliability.core.decision.Tone

/** A card that rises in once, in sequence with its siblings: motion that
 *  shows reading order, never decoration. Respects the system's reduced
 *  motion through the animation scale. */
@Composable
fun RisingCard(order: Int = 0, modifier: Modifier = Modifier, content: @Composable () -> Unit) {
    var shown by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) { shown = true }
    AnimatedVisibility(
        visible = shown,
        enter = fadeIn(tween(260, delayMillis = order * 70)) + slideInVertically(tween(320, delayMillis = order * 70)) { it / 6 },
    ) {
        Card(
            modifier = modifier.fillMaxWidth().padding(bottom = 12.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        ) { Column(Modifier.padding(16.dp)) { content() } }
    }
}

@Composable
fun SectionTitle(text: String, count: Int? = null) {
    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(bottom = 8.dp)) {
        Text(text, style = MaterialTheme.typography.titleMedium)
        if (count != null) {
            Spacer(Modifier.width(8.dp))
            Text(count.toString(), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary)
        }
    }
}

/** The five verdict states, as text with a colour, never colour alone. */
@Composable
fun ToneBadge(tone: Tone, label: String? = null) {
    val (colour, background) = when (tone) {
        Tone.GOOD -> Tokens.Good to Color(0xFFDCFCE7)
        Tone.OKAY -> Tokens.Amber to Tokens.AmberSoft
        Tone.BAD -> Tokens.Danger to Color(0xFFFEE2E2)
        Tone.UNASSESSED -> MaterialTheme.colorScheme.onSurfaceVariant to MaterialTheme.colorScheme.surfaceVariant
        Tone.UNAVAILABLE -> MaterialTheme.colorScheme.onSurfaceVariant to MaterialTheme.colorScheme.surfaceVariant
    }
    val text = label ?: t("tone." + tone.name.lowercase())
    Text(
        text,
        style = MaterialTheme.typography.labelSmall,
        color = colour,
        modifier = Modifier.background(background, RoundedCornerShape(999.dp)).padding(horizontal = 8.dp, vertical = 3.dp)
            .semantics { contentDescription = text },
    )
}

@Composable
fun Loading(label: String = t("common.loading")) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
        modifier = Modifier.padding(16.dp).semantics { contentDescription = label }) {
        CircularProgressIndicator(Modifier.height(20.dp).width(20.dp), strokeWidth = 2.dp)
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
fun ErrorState(message: String, onRetry: (() -> Unit)? = null) {
    Column(Modifier.padding(16.dp)) {
        Text(message, color = MaterialTheme.colorScheme.error)
        if (onRetry != null) {
            Spacer(Modifier.height(8.dp))
            Button(onClick = onRetry) { Text(t("common.retry")) }
        }
    }
}

@Composable
fun Muted(text: String, modifier: Modifier = Modifier) {
    Text(text, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = modifier)
}

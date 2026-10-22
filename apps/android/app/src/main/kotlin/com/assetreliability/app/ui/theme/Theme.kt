package com.assetreliability.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

/** The web design tokens (frontend/src/shared/styles/tokens.css): light
 *  canvas, navy navigation, teal accent, amber for attention. Verdict
 *  colours are the same five the web uses. */
object Tokens {
    val Navy = Color(0xFF111A2E)
    val Canvas = Color(0xFFF8FAFC)
    val Surface = Color(0xFFFFFFFF)
    val Text = Color(0xFF0F172A)
    val Muted = Color(0xFF475569)
    val Teal = Color(0xFF006B73)
    val TealSoft = Color(0xFFDFF5F4)
    val Amber = Color(0xFFB45309)
    val AmberSoft = Color(0xFFFEF3C7)
    val Danger = Color(0xFFB91C1C)
    val Good = Color(0xFF15803D)
    val DarkSurface = Color(0xFF0D182A)
    val DarkText = Color(0xFFEDF4FC)
    val DarkTeal = Color(0xFF55DFD2)
}

private val Light = lightColorScheme(
    primary = Tokens.Teal, onPrimary = Color.White, primaryContainer = Tokens.TealSoft, onPrimaryContainer = Tokens.Navy,
    secondary = Tokens.Navy, onSecondary = Color.White,
    tertiary = Tokens.Amber, tertiaryContainer = Tokens.AmberSoft,
    background = Tokens.Canvas, onBackground = Tokens.Text,
    surface = Tokens.Surface, onSurface = Tokens.Text, onSurfaceVariant = Tokens.Muted,
    error = Tokens.Danger,
)

private val Dark = darkColorScheme(
    primary = Tokens.DarkTeal, onPrimary = Tokens.Navy, primaryContainer = Color(0xFF123B3F), onPrimaryContainer = Tokens.DarkText,
    secondary = Tokens.DarkTeal, background = Tokens.Navy, onBackground = Tokens.DarkText,
    surface = Tokens.DarkSurface, onSurface = Tokens.DarkText, onSurfaceVariant = Color(0xFFA7B4C6),
    tertiary = Color(0xFFFBBF24), error = Color(0xFFF87171),
)

val AppTypography = Typography(
    headlineMedium = TextStyle(fontSize = 24.sp, fontWeight = FontWeight.SemiBold, lineHeight = 30.sp),
    titleLarge = TextStyle(fontSize = 19.sp, fontWeight = FontWeight.SemiBold, lineHeight = 26.sp),
    titleMedium = TextStyle(fontSize = 16.sp, fontWeight = FontWeight.SemiBold, lineHeight = 22.sp),
    bodyLarge = TextStyle(fontSize = 16.sp, lineHeight = 24.sp),
    bodyMedium = TextStyle(fontSize = 14.sp, lineHeight = 21.sp),
    labelSmall = TextStyle(fontSize = 11.sp, fontWeight = FontWeight.SemiBold, letterSpacing = 0.6.sp),
)

@Composable
fun AssetReliabilityTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (isSystemInDarkTheme()) Dark else Light,
        typography = AppTypography,
        content = content,
    )
}

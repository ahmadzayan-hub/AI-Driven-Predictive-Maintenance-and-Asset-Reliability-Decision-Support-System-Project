package com.assetreliability.app.ui

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Insights
import androidx.compose.material.icons.filled.Memory
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.VerifiedUser
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.unit.LayoutDirection
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import androidx.navigation.NavType
import com.assetreliability.app.ui.screens.AnalysesScreen
import com.assetreliability.app.ui.screens.ApprovalsScreen
import com.assetreliability.app.ui.screens.AssistantScreen
import com.assetreliability.app.ui.screens.CommandCentreScreen
import com.assetreliability.app.ui.screens.MemoryScreen
import com.assetreliability.app.ui.screens.PresentationScreen
import com.assetreliability.app.ui.screens.SettingsScreen
import com.assetreliability.app.ui.screens.SettingsViewModel
import com.assetreliability.app.ui.theme.AssetReliabilityTheme

private data class Destination(val route: String, val key: String, val icon: androidx.compose.ui.graphics.vector.ImageVector)

private val destinations = listOf(
    Destination("command", "nav.command", Icons.Filled.Dashboard),
    Destination("analyses", "nav.analyses", Icons.Filled.Insights),
    Destination("approvals", "nav.approvals", Icons.Filled.VerifiedUser),
    Destination("memory", "nav.memory", Icons.Filled.Memory),
    Destination("settings", "nav.settings", Icons.Filled.Settings),
)

/** The shell: a bottom bar with the five places a manager opens, the
 *  Command Centre first. Arabic flips the layout direction. */
@Composable
fun AppRoot(settingsViewModel: SettingsViewModel = hiltViewModel()) {
    val settings by settingsViewModel.settings.collectAsStateWithLifecycle()
    val translator = Translator(settings?.language ?: "en")
    val direction = if (translator.isArabic) LayoutDirection.Rtl else LayoutDirection.Ltr
    CompositionLocalProvider(LocalTranslator provides translator, LocalLayoutDirection provides direction) {
        AssetReliabilityTheme {
          key(settings?.serverUrl, settings?.token) {
            val nav = rememberNavController()
            val backStack by nav.currentBackStackEntryAsState()
            val current = backStack?.destination?.route?.substringBefore("/")
            Scaffold(bottomBar = {
                NavigationBar {
                    destinations.forEach { destination ->
                        NavigationBarItem(
                            selected = current == destination.route,
                            onClick = { nav.navigate(destination.route) { launchSingleTop = true; popUpTo("command") } },
                            icon = { Icon(destination.icon, contentDescription = null) },
                            label = { Text(t(destination.key)) },
                        )
                    }
                }
            }) { padding ->
                NavHost(nav, startDestination = "command", modifier = Modifier.padding(padding)) {
                    composable("command") { CommandCentreScreen(onPresent = { nav.navigate("present/$it") }) }
                    composable("present/{runId}", arguments = listOf(navArgument("runId") { type = NavType.StringType })) {
                        PresentationScreen(runId = it.arguments?.getString("runId") ?: "", onBack = { nav.popBackStack() })
                    }
                    composable("analyses") { AnalysesScreen() }
                    composable("approvals") { ApprovalsScreen() }
                    composable("memory") { MemoryScreen(onAssistant = { nav.navigate("assistant") }) }
                    composable("assistant") { AssistantScreen(onBack = { nav.popBackStack() }) }
                    composable("settings") { SettingsScreen() }
                }
            }
          }
        }
    }
}

package com.example.pricecomparisonapp.ui.theme

import android.app.Activity
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat
import com.google.accompanist.systemuicontroller.rememberSystemUiController

private val LightColorScheme = lightColorScheme(
    primary = ColorPrimary,
    onPrimary = White,
    primaryContainer = ColorPrimaryLight,
    onPrimaryContainer = ColorPrimaryDark,
    secondary = ColorAccent,
    onSecondary = White,
    secondaryContainer = PaleOrange,
    onSecondaryContainer = ColorPrimaryDark,
    tertiary = MediumBlue,
    onTertiary = White,
    tertiaryContainer = LightBlue,
    onTertiaryContainer = ColorPrimaryDark,
    error = AlertRed,
    onError = White,
    errorContainer = Color(0xFFFFDAD6),
    onErrorContainer = Color(0xFF410002),
    background = BackgroundColor,
    onBackground = TextPrimary,
    surface = White,
    onSurface = TextPrimary,
    surfaceVariant = Gray100,
    onSurfaceVariant = TextSecondary,
    outline = Gray300,
    inverseOnSurface = White,
    inverseSurface = TextPrimary,
    inversePrimary = ColorPrimaryLight,
    surfaceTint = ColorPrimary,
    outlineVariant = Gray200,
    scrim = Black
)

private val DarkColorScheme = darkColorScheme(
    primary = ColorPrimaryLight,
    onPrimary = ColorPrimaryDark,
    primaryContainer = ColorPrimary,
    onPrimaryContainer = ColorPrimaryLight,
    secondary = PaleOrange,
    onSecondary = Color(0xFF3A1F00),
    secondaryContainer = Color(0xFF542F00),
    onSecondaryContainer = PaleOrange,
    tertiary = LightBlue,
    onTertiary = Color(0xFF003355),
    tertiaryContainer = Color(0xFF004A77),
    onTertiaryContainer = LightBlue,
    error = Color(0xFFFFB4AB),
    onError = Color(0xFF690005),
    errorContainer = Color(0xFF93000A),
    onErrorContainer = Color(0xFFFFDAD6),
    background = Color(0xFF1C1B1F),
    onBackground = Color(0xFFE6E1E5),
    surface = Color(0xFF1C1B1F),
    onSurface = Color(0xFFE6E1E5),
    surfaceVariant = Color(0xFF49454F),
    onSurfaceVariant = Color(0xFFCAC4D0),
    outline = Color(0xFF938F99),
    inverseOnSurface = Color(0xFF1C1B1F),
    inverseSurface = Color(0xFFE6E1E5),
    inversePrimary = ColorPrimary,
    surfaceTint = ColorPrimaryLight,
    outlineVariant = Color(0xFF49454F),
    scrim = Black
)

@Composable
fun PriceComparisonAppTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    // Dynamic color is available on Android 12+
    dynamicColor: Boolean = false, // Disabled by default to use brand colors
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    val view = LocalView.current
    if (!view.isInEditMode) {
        val systemUiController = rememberSystemUiController()
        val statusBarColor = if (darkTheme) ColorPrimaryDark else ColorPrimaryDark

        SideEffect {
            systemUiController.setSystemBarsColor(
                color = statusBarColor,
                darkIcons = false
            )

            val window = (view.context as Activity).window
            window.statusBarColor = statusBarColor.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = false
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}
package com.example.pricecomparisonapp.screens

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ShoppingCart
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.pricecomparisonapp.ui.theme.*
import kotlinx.coroutines.delay

@Composable
fun SplashScreen(
    onSplashFinished: () -> Unit
) {
    // Animation states
    val logoScale = remember { Animatable(0.5f) }
    val logoAlpha = remember { Animatable(0f) }
    val textAlpha = remember { Animatable(0f) }
    val progressAlpha = remember { Animatable(0f) }

    LaunchedEffect(Unit) {
        // Logo animation
        logoAlpha.animateTo(
            targetValue = 1f,
            animationSpec = tween(600)
        )
        logoScale.animateTo(
            targetValue = 1f,
            animationSpec = spring(
                dampingRatio = Spring.DampingRatioMediumBouncy,
                stiffness = Spring.StiffnessLow
            )
        )

        // Text animations with delay
        delay(400)
        textAlpha.animateTo(
            targetValue = 1f,
            animationSpec = tween(600)
        )

        // Progress indicator
        delay(200)
        progressAlpha.animateTo(
            targetValue = 1f,
            animationSpec = tween(400)
        )

        // Minimum splash duration
        delay(1200)
        onSplashFinished()
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(ColorPrimary),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
            modifier = Modifier.padding(24.dp)
        ) {
            // Logo
            Icon(
                imageVector = Icons.Filled.ShoppingCart,
                contentDescription = "Champion Cart Logo",
                modifier = Modifier
                    .size(150.dp)
                    .scale(logoScale.value)
                    .alpha(logoAlpha.value),
                tint = Color.White
            )

            Spacer(modifier = Modifier.height(24.dp))

            // App Name
            Text(
                text = "Champion Cart",
                fontSize = 32.sp,
                fontWeight = FontWeight.Bold,
                color = Color.White,
                modifier = Modifier.alpha(textAlpha.value)
            )

            // Tagline
            Text(
                text = "השוואת מחירים חכמה",
                fontSize = 18.sp,
                color = Color.White.copy(alpha = 0.9f),
                modifier = Modifier
                    .padding(top = 12.dp)
                    .alpha(textAlpha.value),
                textAlign = TextAlign.Center
            )

            Spacer(modifier = Modifier.height(48.dp))

            // Loading indicator
            CircularProgressIndicator(
                modifier = Modifier
                    .size(48.dp)
                    .alpha(progressAlpha.value),
                color = ColorAccent,
                trackColor = Color.White.copy(alpha = 0.3f),
                strokeWidth = 3.dp
            )

            Spacer(modifier = Modifier.height(80.dp))

            // Version
            Text(
                text = "גרסה 1.0",
                fontSize = 12.sp,
                color = Color.White.copy(alpha = 0.7f),
                modifier = Modifier.alpha(textAlpha.value)
            )
        }
    }
}
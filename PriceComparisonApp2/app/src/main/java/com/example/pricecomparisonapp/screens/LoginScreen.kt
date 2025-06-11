// com/example/pricecomparisonapp/screens/LoginScreen.kt
package com.example.pricecomparisonapp.screens

import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.scale
import androidx.compose.ui.focus.FocusDirection
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.pricecomparisonapp.R
import com.example.pricecomparisonapp.ui.theme.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@Composable
fun LoginScreen(
    onLoginSuccess: () -> Unit,
    onLogin: (email: String, password: String, rememberMe: Boolean) -> Unit,
    onRegister: (email: String, password: String) -> Unit
) {
    var isLoginMode by remember { mutableStateOf(true) }
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var rememberMe by remember { mutableStateOf(true) }
    var passwordVisible by remember { mutableStateOf(false) }
    var isLoading by remember { mutableStateOf(false) }

    var emailError by remember { mutableStateOf<String?>(null) }
    var passwordError by remember { mutableStateOf<String?>(null) }

    val focusManager = LocalFocusManager.current
    val scope = rememberCoroutineScope()

    // Animation states
    val logoScale = remember { Animatable(0.7f) }
    val contentAlpha = remember { Animatable(0f) }

    LaunchedEffect(Unit) {
        logoScale.animateTo(
            targetValue = 1f,
            animationSpec = spring(
                dampingRatio = Spring.DampingRatioMediumBouncy,
                stiffness = Spring.StiffnessLow
            )
        )
        contentAlpha.animateTo(
            targetValue = 1f,
            animationSpec = tween(800)
        )
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundColor)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(modifier = Modifier.height(40.dp))

            // Logo
            Icon(
                imageVector = Icons.Filled.ShoppingCart,
                contentDescription = "Champion Cart Logo",
                modifier = Modifier
                    .size(120.dp)
                    .scale(logoScale.value),
                tint = ColorPrimary
            )

            // App Name
            Text(
                text = "Champion Cart",
                fontSize = 28.sp,
                fontWeight = FontWeight.Bold,
                color = ColorPrimary,
                modifier = Modifier
                    .padding(top = 16.dp)
                    .animateContentSize()
            )

            Spacer(modifier = Modifier.height(24.dp))

            // Login/Register Card
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .animateContentSize(),
                shape = RoundedCornerShape(16.dp),
                elevation = CardDefaults.cardElevation(defaultElevation = 4.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White)
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    // Title
                    Text(
                        text = if (isLoginMode) "התחברות" else "הרשמה",
                        fontSize = 22.sp,
                        fontWeight = FontWeight.Bold,
                        color = ColorPrimary,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.padding(bottom = 16.dp)
                    )

                    // Email Field
                    OutlinedTextField(
                        value = email,
                        onValueChange = {
                            email = it
                            emailError = validateEmail(it)
                        },
                        label = { Text("מייל") },
                        leadingIcon = {
                            Icon(Icons.Filled.Email, contentDescription = "Email", tint = ColorPrimary)
                        },
                        trailingIcon = {
                            if (email.isNotEmpty()) {
                                IconButton(onClick = { email = "" }) {
                                    Icon(Icons.Filled.Clear, contentDescription = "Clear")
                                }
                            }
                        },
                        isError = emailError != null,
                        supportingText = {
                            if (emailError != null) {
                                Text(emailError!!, color = MaterialTheme.colorScheme.error)
                            }
                        },
                        keyboardOptions = KeyboardOptions(
                            keyboardType = KeyboardType.Email,
                            imeAction = ImeAction.Next
                        ),
                        keyboardActions = KeyboardActions(
                            onNext = { focusManager.moveFocus(FocusDirection.Down) }
                        ),
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        shape = RoundedCornerShape(12.dp)
                    )

                    Spacer(modifier = Modifier.height(8.dp))

                    // Password Field
                    OutlinedTextField(
                        value = password,
                        onValueChange = {
                            password = it
                            passwordError = validatePassword(it)
                        },
                        label = { Text("סיסמה") },
                        leadingIcon = {
                            Icon(Icons.Filled.Lock, contentDescription = "Password", tint = ColorPrimary)
                        },
                        trailingIcon = {
                            IconButton(onClick = { passwordVisible = !passwordVisible }) {
                                Icon(
                                    imageVector = if (passwordVisible) Icons.Filled.VisibilityOff else Icons.Filled.Visibility,
                                    contentDescription = if (passwordVisible) "Hide password" else "Show password"
                                )
                            }
                        },
                        visualTransformation = if (passwordVisible) VisualTransformation.None else PasswordVisualTransformation(),
                        isError = passwordError != null,
                        supportingText = {
                            if (passwordError != null) {
                                Text(passwordError!!, color = MaterialTheme.colorScheme.error)
                            }
                        },
                        keyboardOptions = KeyboardOptions(
                            keyboardType = KeyboardType.Password,
                            imeAction = ImeAction.Done
                        ),
                        keyboardActions = KeyboardActions(
                            onDone = {
                                focusManager.clearFocus()
                                handleSubmit(
                                    isLoginMode, email, password, rememberMe,
                                    onLogin, onRegister,
                                    { emailError = it }, { passwordError = it }, { isLoading = it }
                                )
                            }
                        ),
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        shape = RoundedCornerShape(12.dp)
                    )

                    // Remember Me Checkbox (only for login)
                    if (isLoginMode) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(top = 8.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Checkbox(
                                checked = rememberMe,
                                onCheckedChange = { rememberMe = it },
                                colors = CheckboxDefaults.colors(
                                    checkedColor = ColorPrimary
                                )
                            )
                            Text(
                                text = "זכור אותי",
                                color = TextPrimary,
                                modifier = Modifier.padding(start = 4.dp)
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(24.dp))

                    // Submit Button
                    Button(
                        onClick = {
                            handleSubmit(
                                isLoginMode, email, password, rememberMe,
                                onLogin, onRegister,
                                { emailError = it }, { passwordError = it }, { isLoading = it }
                            )
                        },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(48.dp),
                        enabled = !isLoading,
                        shape = RoundedCornerShape(24.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = ColorPrimary
                        )
                    ) {
                        if (isLoading) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(24.dp),
                                color = Color.White,
                                strokeWidth = 2.dp
                            )
                        } else {
                            Icon(
                                imageVector = if (isLoginMode) Icons.Filled.Login else Icons.Filled.PersonAdd,
                                contentDescription = null,
                                modifier = Modifier.padding(end = 8.dp)
                            )
                            Text(
                                text = if (isLoginMode) "התחבר" else "הרשם",
                                fontSize = 16.sp
                            )
                        }
                    }

                    // Forgot Password (only for login)
                    if (isLoginMode) {
                        TextButton(
                            onClick = { /* TODO: Implement forgot password */ },
                            modifier = Modifier.padding(top = 8.dp)
                        ) {
                            Text(
                                text = "שכחת סיסמה?",
                                color = ColorAccent
                            )
                        }
                    }
                }
            }

            // Toggle Login/Register
            OutlinedButton(
                onClick = {
                    isLoginMode = !isLoginMode
                    // Clear errors when switching modes
                    emailError = null
                    passwordError = null
                },
                modifier = Modifier
                    .padding(top = 24.dp)
                    .animateContentSize(),
                shape = RoundedCornerShape(24.dp),
                border = ButtonDefaults.outlinedButtonBorder.copy(width = 1.dp)
            ) {
                Icon(
                    imageVector = if (isLoginMode) Icons.Filled.PersonAdd else Icons.Filled.Login,
                    contentDescription = null,
                    modifier = Modifier.padding(end = 8.dp),
                    tint = ColorPrimary
                )
                Text(
                    text = if (isLoginMode) "הרשמה למשתמש חדש" else "כבר קיים משתמש? התחבר",
                    color = ColorPrimary
                )
            }

            Spacer(modifier = Modifier.height(40.dp))
        }
    }
}

private fun validateEmail(email: String): String? {
    return when {
        email.isEmpty() -> "נא להזין מייל"
        !android.util.Patterns.EMAIL_ADDRESS.matcher(email).matches() -> "נא להזין מייל תקין"
        else -> null
    }
}

private fun validatePassword(password: String): String? {
    return when {
        password.isEmpty() -> "נא להזין סיסמה"
        password.length < 6 -> "הסיסמה חייבת להכיל לפחות 6 תווים"
        else -> null
    }
}

private fun handleSubmit(
    isLoginMode: Boolean,
    email: String,
    password: String,
    rememberMe: Boolean,
    onLogin: (String, String, Boolean) -> Unit,
    onRegister: (String, String) -> Unit,
    setEmailError: (String?) -> Unit,
    setPasswordError: (String?) -> Unit,
    setLoading: (Boolean) -> Unit
) {
    val emailErr = validateEmail(email)
    val passwordErr = validatePassword(password)

    setEmailError(emailErr)
    setPasswordError(passwordErr)

    if (emailErr == null && passwordErr == null) {
        setLoading(true)
        if (isLoginMode) {
            onLogin(email, password, rememberMe)
        } else {
            onRegister(email, password)
        }
    }
}
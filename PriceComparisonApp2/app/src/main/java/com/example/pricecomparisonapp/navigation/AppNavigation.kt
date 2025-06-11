package com.example.pricecomparisonapp.navigation

import androidx.compose.runtime.*
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.example.pricecomparisonapp.screens.LoginScreen
import com.example.pricecomparisonapp.MainScreen
import com.example.pricecomparisonapp.CartViewModel

sealed class AppScreen(val route: String) {
    object Login : AppScreen("login")
    object Main : AppScreen("main")
}

@Composable
fun AppNavigation(
    cartViewModel: CartViewModel,
    citiesList: List<String>,
    onAddToCart: (com.example.pricecomparisonapp.Item) -> Unit,
    onFetchCheapestCart: (String, List<com.example.pricecomparisonapp.Item>, (String, Double) -> Unit) -> Unit,
    onLogin: (email: String, password: String, rememberMe: Boolean) -> Unit,
    onRegister: (email: String, password: String) -> Unit,
    startDestination: String = AppScreen.Login.route,
    saveCart: (String, String, List<com.example.pricecomparisonapp.Item>, () -> Unit) -> Unit,
    fetchSavedCarts: (String, String, (List<com.example.pricecomparisonapp.screens.SavedCart>) -> Unit) -> Unit,
    searchItems: (String, String, (List<com.example.pricecomparisonapp.Item>) -> Unit) -> Unit
) {
    val navController = rememberNavController()

    NavHost(
        navController = navController,
        startDestination = startDestination
    ) {
        composable(AppScreen.Login.route) {
            LoginScreen(
                onLoginSuccess = {
                    navController.navigate(AppScreen.Main.route) {
                        popUpTo(AppScreen.Login.route) { inclusive = true }
                    }
                },
                onLogin = onLogin,
                onRegister = onRegister
            )
        }

        composable(AppScreen.Main.route) {
            MainScreen(
                cartViewModel = cartViewModel,
                citiesList = citiesList,
                onAddToCart = onAddToCart,
                onFetchCheapestCart = onFetchCheapestCart,
                saveCart = saveCart,
                fetchSavedCarts = fetchSavedCarts,
                searchItems = searchItems
            )
        }
    }
}
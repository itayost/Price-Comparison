package com.example.pricecomparisonapp

import android.content.Context
import android.content.Intent
import android.util.Log
import android.widget.Toast
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.example.pricecomparisonapp.screens.HomeScreen
import com.example.pricecomparisonapp.screens.SearchScreen
import com.example.pricecomparisonapp.screens.SettingsScreen
import com.example.pricecomparisonapp.screens.SavedCart
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

sealed class Screen(val route: String, val title: String, val icon: androidx.compose.ui.graphics.vector.ImageVector) {
    object Home : Screen("home", "ראשי", Icons.Filled.Home)
    object Search : Screen("search", "חיפוש", Icons.Filled.Search)
    object Settings : Screen("settings", "הגדרות", Icons.Filled.Settings)
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    cartViewModel: CartViewModel,
    citiesList: List<String>,
    onAddToCart: (Item) -> Unit,
    onFetchCheapestCart: (String, List<Item>, (String, Double) -> Unit) -> Unit,
    saveCart: (String, String, List<Item>, () -> Unit) -> Unit,
    fetchSavedCarts: (String, String, (List<SavedCart>) -> Unit) -> Unit,
    searchItems: (String, String, (List<Item>) -> Unit) -> Unit
) {
    val navController = rememberNavController()
    val items = listOf(Screen.Home, Screen.Search, Screen.Settings)

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.app_name)) },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface,
                    titleContentColor = MaterialTheme.colorScheme.primary
                )
            )
        },
        bottomBar = {
            NavigationBar {
                val navBackStackEntry by navController.currentBackStackEntryAsState()
                val currentDestination = navBackStackEntry?.destination

                items.forEach { screen ->
                    NavigationBarItem(
                        icon = { Icon(screen.icon, contentDescription = screen.title) },
                        label = { Text(screen.title) },
                        selected = currentDestination?.hierarchy?.any { it.route == screen.route } == true,
                        onClick = {
                            navController.navigate(screen.route) {
                                popUpTo(navController.graph.findStartDestination().id) {
                                    saveState = true
                                }
                                launchSingleTop = true
                                restoreState = true
                            }
                        }
                    )
                }
            }
        }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = Screen.Home.route,
            modifier = Modifier.padding(innerPadding)
        ) {
            composable(Screen.Home.route) {
                val context = LocalContext.current
                val sharedPreferences = context.getSharedPreferences("AppPreferences", Context.MODE_PRIVATE)
                val userPrefs = context.getSharedPreferences("user_prefs", Context.MODE_PRIVATE)

                var currentCity by remember {
                    mutableStateOf(sharedPreferences.getString("location", "") ?: "")
                }
                var savedCarts by remember { mutableStateOf<List<SavedCart>>(emptyList()) }

                // Fetch saved carts when entering home screen
                LaunchedEffect(Unit) {
                    val email = userPrefs.getString("user_email", "") ?: ""
                    if (email.isNotEmpty() && currentCity.isNotEmpty()) {
                        fetchSavedCarts(email, currentCity) { carts ->
                            savedCarts = carts
                        }
                    }
                }

                HomeScreen(
                    cartViewModel = cartViewModel,
                    citiesList = citiesList,
                    savedCarts = savedCarts,
                    currentCity = currentCity,
                    onCityChange = {
                        // Navigate to settings to change city
                        navController.navigate(Screen.Settings.route)
                    },
                    onFetchCheapestCart = onFetchCheapestCart,
                    onSaveCart = { cartName ->
                        val email = userPrefs.getString("user_email", "") ?: ""
                        if (email.isNotEmpty()) {
                            saveCart(email, cartName, cartViewModel.getCartAsList()) {
                                // Refresh saved carts
                                fetchSavedCarts(email, currentCity) { carts ->
                                    savedCarts = carts
                                }
                            }
                        }
                    },
                    onLoadCart = { savedCart ->
                        cartViewModel.clearCart()
                        savedCart.items.forEach { item ->
                            cartViewModel.addToCart(item)
                        }
                        Toast.makeText(context, "עגלה נטענה בהצלחה", Toast.LENGTH_SHORT).show()
                    }
                )
            }
            composable(Screen.Search.route) {
                val context = LocalContext.current
                val sharedPreferences = context.getSharedPreferences("AppPreferences", Context.MODE_PRIVATE)
                val currentCity = sharedPreferences.getString("location", "") ?: ""

                SearchScreen(
                    currentCity = currentCity,
                    onAddToCart = { item, quantity ->
                        // Create item with selected quantity
                        val itemWithQuantity = Item(
                            item_name = item.item_name,
                            quantity = quantity,
                            price = item.price * quantity,
                            store_name = item.store_name,
                            store_id = item.store_id,
                            item_code = item.item_code
                        )

                        onAddToCart(itemWithQuantity)

                        // Show toast message
                        val message = "המוצר '${item.item_name}' נוסף לסל (${quantity} יח')"
                        Toast.makeText(context, message, Toast.LENGTH_SHORT).show()
                    },
                    onSearch = { city, searchTerm ->
                        var searchResults = emptyList<Item>()
                        val latch = CountDownLatch(1)

                        searchItems(city, searchTerm) { results ->
                            searchResults = results
                            latch.countDown()
                        }

                        // Wait for results (in production, use coroutines instead)
                        try {
                            latch.await(5, TimeUnit.SECONDS)
                        } catch (e: Exception) {
                            Log.e("Search", "Timeout waiting for search results")
                        }

                        searchResults
                    }
                )
            }
            composable(Screen.Settings.route) {
                val context = LocalContext.current
                val sharedPreferences = context.getSharedPreferences("AppPreferences", Context.MODE_PRIVATE)
                var currentCity by remember {
                    mutableStateOf(sharedPreferences.getString("location", "") ?: "")
                }

                SettingsScreen(
                    citiesList = citiesList,
                    currentCity = currentCity,
                    onCitySelected = { city ->
                        // Save selected city to SharedPreferences
                        sharedPreferences.edit().putString("location", city).apply()
                        currentCity = city
                        Toast.makeText(context, "העיר עודכנה ל: $city", Toast.LENGTH_SHORT).show()
                    },
                    onLogout = {
                        // Clear cart when logging out
                        cartViewModel.clearCart()

                        // Navigate to login screen by restarting the activity
                        val intent = Intent(context, MainActivity::class.java)
                        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                        context.startActivity(intent)

                        // The MainActivity will check login status and show login screen
                    }
                )
            }
        }
    }
}
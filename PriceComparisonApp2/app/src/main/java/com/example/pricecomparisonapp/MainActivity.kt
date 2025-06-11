package com.example.pricecomparisonapp

import android.content.Context
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.*
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.ViewModelProvider
import com.example.pricecomparisonapp.navigation.AppNavigation
import com.example.pricecomparisonapp.navigation.AppScreen
import com.example.pricecomparisonapp.screens.SavedCart
import com.example.pricecomparisonapp.screens.SplashScreen
import com.example.pricecomparisonapp.ui.theme.PriceComparisonAppTheme
import com.example.pricecomparisonapp.utils.Constants
import com.google.gson.Gson
import com.google.gson.JsonArray
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException

class MainActivity : ComponentActivity() {

    private lateinit var cartViewModel: CartViewModel
    private val client = OkHttpClient()
    private var citiesList by mutableStateOf<List<String>>(emptyList())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        // Initialize ViewModel
        cartViewModel = ViewModelProvider(this)[CartViewModel::class.java]

        setContent {
            PriceComparisonAppTheme {
                var showSplash by remember { mutableStateOf(true) }
                var startDestination by remember { mutableStateOf(AppScreen.Login.route) }

                // Check login status
                LaunchedEffect(Unit) {
                    // Fetch cities list
                    fetchCitiesFromAPI()

                    // Check if user is logged in
                    val userPrefs = getSharedPreferences("user_prefs", Context.MODE_PRIVATE)
                    val isLoggedIn = userPrefs.getBoolean("is_logged_in", false)
                    val rememberMe = userPrefs.getBoolean("remember_me", false)

                    if (isLoggedIn && rememberMe) {
                        startDestination = AppScreen.Main.route
                    }

                    // Show splash for minimum duration
                    delay(2200)
                    showSplash = false
                }

                if (showSplash) {
                    SplashScreen(
                        onSplashFinished = {
                            showSplash = false
                        }
                    )
                } else {
                    AppNavigation(
                        cartViewModel = cartViewModel,
                        citiesList = citiesList,
                        onAddToCart = { item ->
                            cartViewModel.addToCart(item)
                        },
                        onFetchCheapestCart = { city, items, callback ->
                            fetchCheapestCart(city, items, callback)
                        },
                        onLogin = { email, password, rememberMe ->
                            loginUser(email, password, rememberMe)
                        },
                        onRegister = { email, password ->
                            registerUser(email, password)
                        },
                        startDestination = startDestination,
                        saveCart = { email, cartName, items, onComplete ->
                            saveCart(email, cartName, items, onComplete)
                        },
                        fetchSavedCarts = { email, city, callback ->
                            fetchSavedCarts(email, city, callback)
                        },
                        searchItems = { city, searchTerm, callback ->
                            searchItems(city, searchTerm, callback)
                        }
                    )
                }
            }
        }
    }

    private fun fetchCitiesFromAPI() {
        val url = "${Constants.BASE_URL}/cities-list"
        val request = Request.Builder().url(url).build()

        client.newCall(request).enqueue(object : Callback {
            override fun onResponse(call: Call, response: Response) {
                if (response.isSuccessful) {
                    val responseData = response.body?.string()
                    val cityListType = object : TypeToken<List<String>>() {}.type
                    citiesList = Gson().fromJson(responseData, cityListType)

                    // Save to SharedPreferences for offline access
                    val sharedPreferences = getSharedPreferences("AppPreferences", Context.MODE_PRIVATE)
                    sharedPreferences.edit()
                        .putStringSet("citiesList", citiesList.toSet())
                        .apply()
                }
            }

            override fun onFailure(call: Call, e: IOException) {
                Log.e("API_ERROR", "Failed to fetch cities: ${e.message}")

                // Try to load from SharedPreferences
                val sharedPreferences = getSharedPreferences("AppPreferences", Context.MODE_PRIVATE)
                val savedCities = sharedPreferences.getStringSet("citiesList", emptySet())
                citiesList = savedCities?.toList() ?: emptyList()
            }
        })
    }

    private fun loginUser(email: String, password: String, rememberMe: Boolean) {
        val url = "${Constants.BASE_URL}/login"
        val requestBody = Gson().toJson(mapOf("email" to email, "password" to password))
        val request = Request.Builder()
            .url(url)
            .post(requestBody.toRequestBody("application/json".toMediaType()))
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onResponse(call: Call, response: Response) {
                runOnUiThread {
                    if (response.isSuccessful) {
                        // Save user data
                        val userPrefs = getSharedPreferences("user_prefs", Context.MODE_PRIVATE)
                        userPrefs.edit().apply {
                            putString("user_email", email)
                            putBoolean("remember_me", rememberMe)
                            putBoolean("is_logged_in", true)
                            apply()
                        }

                        Toast.makeText(applicationContext, "התחברת בהצלחה!", Toast.LENGTH_SHORT).show()

                        // Navigation is handled by the login screen
                    } else {
                        Toast.makeText(applicationContext, "פרטי התחברות שגויים", Toast.LENGTH_SHORT).show()
                    }
                }
            }

            override fun onFailure(call: Call, e: IOException) {
                runOnUiThread {
                    Log.e("API_ERROR", "Failed to login: ${e.message}")
                    Toast.makeText(applicationContext, "בעיית תקשורת עם השרת", Toast.LENGTH_SHORT).show()
                }
            }
        })
    }

    private fun registerUser(email: String, password: String) {
        val url = "${Constants.BASE_URL}/register"
        val requestBody = Gson().toJson(mapOf("email" to email, "password" to password))
        val request = Request.Builder()
            .url(url)
            .post(requestBody.toRequestBody("application/json".toMediaType()))
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onResponse(call: Call, response: Response) {
                runOnUiThread {
                    if (response.isSuccessful) {
                        Toast.makeText(applicationContext, "ההרשמה הושלמה בהצלחה!", Toast.LENGTH_SHORT).show()
                    } else {
                        val responseBody = response.body?.string() ?: ""
                        if (responseBody.contains("exists")) {
                            Toast.makeText(applicationContext, "מייל זה כבר קיים במערכת", Toast.LENGTH_SHORT).show()
                        } else {
                            Toast.makeText(applicationContext, "ההרשמה נכשלה", Toast.LENGTH_SHORT).show()
                        }
                    }
                }
            }

            override fun onFailure(call: Call, e: IOException) {
                runOnUiThread {
                    Log.e("API_ERROR", "Failed to register: ${e.message}")
                    Toast.makeText(applicationContext, "בעיית תקשורת עם השרת", Toast.LENGTH_SHORT).show()
                }
            }
        })
    }

    private fun fetchCheapestCart(city: String, cartItems: List<Item>, callback: (String, Double) -> Unit) {
        if (cartItems.isEmpty()) {
            runOnUiThread {
                Toast.makeText(this, "אין פריטים בעגלה", Toast.LENGTH_SHORT).show()
            }
            return
        }

        val jsonItems = cartItems.map { item ->
            mapOf("item_name" to item.item_name, "quantity" to item.quantity)
        }

        val requestBody = Gson().toJson(mapOf("city" to city, "items" to jsonItems))

        val request = Request.Builder()
            .url("${Constants.BASE_URL}/cheapest-cart-all-chains")
            .post(requestBody.toRequestBody("application/json".toMediaType()))
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onResponse(call: Call, response: Response) {
                runOnUiThread {
                    try {
                        if (response.isSuccessful) {
                            val responseBody = response.body?.string()
                            if (!responseBody.isNullOrEmpty()) {
                                val responseMap = Gson().fromJson(responseBody, Map::class.java)
                                val totalPrice = responseMap["total_price"] as Double
                                val chain = responseMap["chain"] as String
                                val storeId = responseMap["store_id"] as String

                                val storeText = when (chain) {
                                    "shufersal" -> "שופרסל"
                                    "victory" -> "ויקטורי"
                                    else -> chain
                                }

                                val fullStoreText = "$storeText סניף $storeId"

                                // Update ViewModel
                                cartViewModel.updateCheapestCart(fullStoreText, totalPrice)

                                // Call the callback
                                callback(fullStoreText, totalPrice)

                                Toast.makeText(this@MainActivity, "המחיר הזול ביותר נמצא!", Toast.LENGTH_SHORT).show()
                            }
                        } else {
                            Toast.makeText(this@MainActivity, "שגיאה בחיפוש המחיר הזול ביותר", Toast.LENGTH_SHORT).show()
                        }
                    } catch (e: Exception) {
                        Log.e("API_ERROR", "Error parsing response: ${e.message}")
                        Toast.makeText(this@MainActivity, "שגיאה בעיבוד התשובה", Toast.LENGTH_SHORT).show()
                    }
                }
            }

            override fun onFailure(call: Call, e: IOException) {
                runOnUiThread {
                    Log.e("API_ERROR", "Network error: ${e.message}")
                    Toast.makeText(this@MainActivity, "שגיאת רשת", Toast.LENGTH_SHORT).show()
                }
            }
        })
    }

    private fun saveCart(email: String, cartName: String, items: List<Item>, onComplete: () -> Unit) {
        val url = "${Constants.BASE_URL}/savecart"
        val cartData = mapOf(
            "email" to email,
            "cart_name" to cartName,
            "items" to items
        )

        val jsonBody = Gson().toJson(cartData)
        val requestBody = jsonBody.toRequestBody("application/json".toMediaType())

        val request = Request.Builder()
            .url(url)
            .post(requestBody)
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onResponse(call: Call, response: Response) {
                runOnUiThread {
                    if (response.isSuccessful) {
                        Toast.makeText(this@MainActivity, "העגלה נשמרה בהצלחה", Toast.LENGTH_SHORT).show()
                        onComplete()
                    } else {
                        Toast.makeText(this@MainActivity, "שגיאה בשמירת העגלה", Toast.LENGTH_SHORT).show()
                    }
                }
            }

            override fun onFailure(call: Call, e: IOException) {
                runOnUiThread {
                    Toast.makeText(this@MainActivity, "שגיאת רשת בשמירת העגלה", Toast.LENGTH_SHORT).show()
                }
            }
        })
    }

    private fun fetchSavedCarts(email: String, city: String, callback: (List<SavedCart>) -> Unit) {
        val url = "${Constants.BASE_URL}/savedcarts/$email?city=$city"

        val request = Request.Builder()
            .url(url)
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onResponse(call: Call, response: Response) {
                if (response.isSuccessful) {
                    try {
                        val jsonResponse = response.body?.string()
                        if (!jsonResponse.isNullOrEmpty()) {
                            val responseType = object : TypeToken<Map<String, Any>>() {}.type
                            val responseMap = Gson().fromJson<Map<String, Any>>(jsonResponse, responseType)

                            val savedCartsJson = responseMap["saved_carts"]
                            if (savedCartsJson != null) {
                                val savedCartsType = object : TypeToken<List<SavedCart>>() {}.type
                                val savedCarts: List<SavedCart> = Gson().fromJson(Gson().toJson(savedCartsJson), savedCartsType)

                                runOnUiThread {
                                    callback(savedCarts)
                                }
                            }
                        }
                    } catch (e: Exception) {
                        Log.e("API_ERROR", "Error parsing saved carts: ${e.message}")
                    }
                }
            }

            override fun onFailure(call: Call, e: IOException) {
                Log.e("API_ERROR", "Failed to fetch saved carts: ${e.message}")
            }
        })
    }

    private fun searchItems(city: String, searchTerm: String, callback: (List<Item>) -> Unit) {
        // Search for identical products first
        val url = "${Constants.BASE_URL}/prices/identical-products/$city/${encodeSearchTerm(searchTerm)}"

        val request = Request.Builder().url(url).build()

        client.newCall(request).enqueue(object : Callback {
            override fun onResponse(call: Call, response: Response) {
                val crossChainItems = mutableListOf<Item>()

                if (response.isSuccessful) {
                    try {
                        val responseBody = response.body?.string()
                        if (!responseBody.isNullOrEmpty() && responseBody != "[]") {
                            val jsonArray = Gson().fromJson(responseBody, JsonArray::class.java)

                            // Parse cross-chain items
                            for (i in 0 until jsonArray.size()) {
                                val obj = jsonArray[i].asJsonObject

                                try {
                                    val itemName = obj.get("item_name").asString
                                    val itemCode = if (obj.has("item_code") && !obj.get("item_code").isJsonNull)
                                        obj.get("item_code").asString else null

                                    // Parse price comparison data
                                    val priceComparison = if (obj.has("price_comparison") && !obj.get("price_comparison").isJsonNull) {
                                        val compObj = obj.getAsJsonObject("price_comparison")
                                        val bestDeal = compObj.getAsJsonObject("best_deal")

                                        PriceComparison(
                                            best_deal = BestDeal(
                                                chain = bestDeal.get("chain").asString,
                                                price = bestDeal.get("price").asDouble,
                                                store_id = bestDeal.get("store_id").asString
                                            ),
                                            worst_deal = WorstDeal(
                                                chain = compObj.getAsJsonObject("worst_deal").get("chain").asString,
                                                price = compObj.getAsJsonObject("worst_deal").get("price").asDouble,
                                                store_id = compObj.getAsJsonObject("worst_deal").get("store_id").asString
                                            ),
                                            savings = compObj.get("savings").asDouble,
                                            savings_percent = compObj.get("savings_percent").asDouble
                                        )
                                    } else null

                                    // Parse prices array
                                    val itemPrices = mutableListOf<ItemPrice>()
                                    if (obj.has("prices") && !obj.get("prices").isJsonNull) {
                                        val pricesArray = obj.getAsJsonArray("prices")
                                        for (j in 0 until pricesArray.size()) {
                                            val priceObj = pricesArray[j].asJsonObject
                                            itemPrices.add(ItemPrice(
                                                chain = priceObj.get("chain").asString,
                                                store_id = priceObj.get("store_id").asString,
                                                price = priceObj.get("price").asDouble,
                                                original_name = priceObj.get("original_name").asString,
                                                timestamp = priceObj.get("timestamp").asString
                                            ))
                                        }
                                    }

                                    val bestPrice = priceComparison?.best_deal?.price ?:
                                    itemPrices.minByOrNull { it.price }?.price ?: 0.0
                                    val bestStore = priceComparison?.best_deal?.store_id ?:
                                    itemPrices.minByOrNull { it.price }?.store_id ?: ""
                                    val bestChain = priceComparison?.best_deal?.chain ?:
                                    itemPrices.minByOrNull { it.price }?.chain ?: ""

                                    crossChainItems.add(Item(
                                        item_name = itemName,
                                        quantity = 1,
                                        price = bestPrice,
                                        store_name = bestChain,
                                        store_id = bestStore,
                                        item_code = itemCode,
                                        isCrossChain = true,
                                        prices = itemPrices,
                                        priceComparison = priceComparison
                                    ))
                                } catch (e: Exception) {
                                    Log.e("API_ERROR", "Error parsing cross-chain item: ${e.message}")
                                }
                            }
                        }
                    } catch (e: Exception) {
                        Log.e("API_ERROR", "Error parsing identical products: ${e.message}")
                    }
                }

                // Fetch regular items
                fetchRegularItems(city, searchTerm, crossChainItems, callback)
            }

            override fun onFailure(call: Call, e: IOException) {
                Log.e("API_ERROR", "Network error fetching identical products: ${e.message}")
                // Fall back to regular search
                fetchRegularItems(city, searchTerm, emptyList(), callback)
            }
        })
    }

    private fun fetchRegularItems(
        city: String,
        searchTerm: String,
        crossChainItems: List<Item>,
        callback: (List<Item>) -> Unit
    ) {
        val url = "${Constants.BASE_URL}/prices/by-item/$city/${encodeSearchTerm(searchTerm)}"

        val request = Request.Builder().url(url).build()

        client.newCall(request).enqueue(object : Callback {
            override fun onResponse(call: Call, response: Response) {
                val allItems = mutableListOf<Item>()
                allItems.addAll(crossChainItems)

                if (response.isSuccessful) {
                    try {
                        val responseBody = response.body?.string()
                        if (!responseBody.isNullOrEmpty()) {
                            val jsonArray = Gson().fromJson(responseBody, JsonArray::class.java)

                            val existingItemCodes = crossChainItems
                                .mapNotNull { it.item_code }
                                .toSet()

                            for (i in 0 until jsonArray.size()) {
                                val obj = jsonArray[i].asJsonObject

                                try {
                                    val itemCode = if (obj.has("item_code") && !obj.get("item_code").isJsonNull)
                                        obj.get("item_code").asString else null

                                    // Skip if we already have this item as a cross-chain item
                                    if (itemCode != null && itemCode in existingItemCodes) {
                                        continue
                                    }

                                    allItems.add(Item(
                                        item_name = obj.get("item_name").asString,
                                        quantity = 1,
                                        price = obj.get("price").asDouble,
                                        store_name = obj.get("chain").asString,
                                        store_id = obj.get("store_id").asString,
                                        item_code = itemCode,
                                        isCrossChain = false
                                    ))
                                } catch (e: Exception) {
                                    Log.e("API_ERROR", "Error parsing regular item: ${e.message}")
                                }
                            }
                        }
                    } catch (e: Exception) {
                        Log.e("API_ERROR", "Error parsing regular items: ${e.message}")
                    }
                }

                // Sort and return results
                val sortedItems = sortItems(allItems, searchTerm)
                runOnUiThread {
                    callback(sortedItems)
                }
            }

            override fun onFailure(call: Call, e: IOException) {
                Log.e("API_ERROR", "Network error fetching regular items: ${e.message}")
                runOnUiThread {
                    callback(crossChainItems)
                }
            }
        })
    }

    private fun sortItems(items: List<Item>, searchTerm: String): List<Item> {
        val searchTextLowercase = searchTerm.trim().lowercase()

        return items.sortedWith(compareBy<Item> {
            // Priority 0: Cross-chain items at the top
            if (it.isCrossChain) 0 else 1
        }.thenBy {
            // Priority 1: Items that start with the search term
            if (it.item_name.lowercase().startsWith(searchTextLowercase)) 0 else 1
        }.thenBy {
            // Priority 2: Items that contain a word starting with the search term
            val words = it.item_name.split(" ")
            if (words.any { word -> word.lowercase().startsWith(searchTextLowercase) }) 0 else 1
        }.thenBy {
            // Priority 3: Items that contain the search term
            if (it.item_name.lowercase().contains(searchTextLowercase)) 0 else 1
        }.thenBy {
            // Priority 4: For cross-chain items, sort by savings amount (highest first)
            if (it.isCrossChain) -(it.priceComparison?.savings ?: 0.0) else 0.0
        }.thenBy {
            // Priority 5: For regular items, sort by price (lowest first)
            if (!it.isCrossChain) it.price else 0.0
        })
    }

    private fun encodeSearchTerm(term: String): String {
        return try {
            java.net.URLEncoder.encode(term, "UTF-8").replace("+", "%20")
        } catch (e: Exception) {
            term.toCharArray().joinToString("") { char ->
                when {
                    char == ' ' -> "%20"
                    char.code > 127 -> "%${Integer.toHexString(char.code).uppercase()}"
                    else -> char.toString()
                }
            }
        }
    }
}
package com.example.pricecomparisonapp

import android.annotation.SuppressLint
import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.FrameLayout
import android.widget.Spinner
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.fragment.app.Fragment
import androidx.lifecycle.ViewModelProvider
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import okhttp3.*
import java.io.IOException
import androidx.activity.enableEdgeToEdge
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat

class MainActivity : AppCompatActivity() {

    private val client = OkHttpClient()
    private val baseUrl = "http://172.20.28.72:8000" // Change to local IP
    private var citiesList = listOf<String>()
    private lateinit var bottomNavigation: BottomNavigationView
    
    // ViewModel for cart management
    private lateinit var cartViewModel: CartViewModel

    // Define activity result launcher for settings
    private val settingsActivityResultLauncher =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            if (result.resultCode == RESULT_OK) {
                val selectedLocation = result.data?.getStringExtra("selectedLocation")
                selectedLocation?.let {
                    val spinnerLocation = findViewById<Spinner>(R.id.spinnerLocation)
                    val locationIndex = citiesList.indexOf(it)
                    if (locationIndex != -1) {
                        spinnerLocation.setSelection(locationIndex)
                        Toast.makeText(this, "Location selected: $it", Toast.LENGTH_SHORT).show()
                    } else {
                        Toast.makeText(this, "Location not found in list", Toast.LENGTH_SHORT).show()
                    }
                }
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_main)

        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main)) { v, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }

        // Initialize the ViewModel
        cartViewModel = ViewModelProvider(this).get(CartViewModel::class.java)

        // Set up toolbar
        setSupportActionBar(findViewById(R.id.toolbar))
        supportActionBar?.setDisplayShowTitleEnabled(false)

        // Set up bottom navigation
        bottomNavigation = findViewById(R.id.bottomNavigation)

        // Fetch cities for use in fragments
        fetchCitiesFromAPI()

        // Load default fragment
        if (savedInstanceState == null) {
            loadFragment(HomeFragment())
        }

        // Update the bottom navigation listener
        bottomNavigation.setOnNavigationItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_home -> {
                    loadFragment(HomeFragment())
                    true
                }
                R.id.nav_search -> {
                    loadFragment(SearchFragment())
                    true
                }
                R.id.nav_settings -> {
                    // Create and load SettingsFragment instead of launching SettingsActivity
                    val settingsFragment = SettingsFragment()
                    loadFragment(settingsFragment)
                    true
                }
                else -> false
            }
        }
    }

    // Method to expose the location spinner to fragments
    fun getLocationSpinner(): Spinner {
        return findViewById(R.id.spinnerLocation)
    }

    // Method to expose the cities list to fragments
    fun getCitiesList(): List<String> {
        return citiesList
    }

    fun loadFragment(fragment: Fragment) {
        // Make the fragment container visible
        findViewById<FrameLayout>(R.id.fragmentContainer).visibility = View.VISIBLE

        // Send data to fragment if needed
        if (fragment is SettingsFragment) {
            val bundle = Bundle()
            bundle.putStringArrayList("citiesList", ArrayList(citiesList))
            fragment.arguments = bundle
        }

        // Synchronize spinner before loading fragment
        synchronizeLocationSpinner(fragment)

        // Replace the current fragment
        supportFragmentManager.beginTransaction()
            .replace(R.id.fragmentContainer, fragment)
            .commit()
    }

    private fun fetchCitiesFromAPI() {
        val url = "$baseUrl/cities-list"
        val request = Request.Builder().url(url).build()

        client.newCall(request).enqueue(object : Callback {
            override fun onResponse(call: Call, response: Response) {
                if (response.isSuccessful) {
                    val responseData = response.body()?.string()
                    val cityListType = object : TypeToken<List<String>>() {}.type
                    citiesList = Gson().fromJson(responseData, cityListType)

                    // Update the spinner in MainActivity with the cities list
                    runOnUiThread {
                        val spinner = findViewById<Spinner>(R.id.spinnerLocation)
                        val adapter = ArrayAdapter(
                            this@MainActivity,
                            android.R.layout.simple_spinner_item,
                            citiesList
                        )
                        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
                        spinner.adapter = adapter
                        
                        // Set default selection
                        if (citiesList.isNotEmpty()) {
                            // Try to get saved location from SharedPreferences
                            val sharedPreferences = getSharedPreferences("AppPreferences", MODE_PRIVATE)
                            val savedLocation = sharedPreferences.getString("location", citiesList[0])
                            val locationIndex = citiesList.indexOf(savedLocation)
                            if (locationIndex >= 0) {
                                spinner.setSelection(locationIndex)
                            } else {
                                spinner.setSelection(0)
                            }
                            
                            // Save selection changes
                            spinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                                override fun onItemSelected(parent: AdapterView<*>, view: View?, position: Int, id: Long) {
                                    val selectedLocation = parent.getItemAtPosition(position).toString()
                                    with(sharedPreferences.edit()) {
                                        putString("location", selectedLocation)
                                        apply()
                                    }
                                }
                                
                                override fun onNothingSelected(parent: AdapterView<*>?) {}
                            }
                        }
                    }

                    // Notify the current fragment about updated cities list if it's a settings fragment
                    val currentFragment = supportFragmentManager.findFragmentById(R.id.fragmentContainer)
                    if (currentFragment is SettingsFragment) {
                        runOnUiThread {
                            // Update the fragment with cities
                            currentFragment.updateCitiesList(citiesList)
                        }
                    }
                } else {
                    runOnUiThread {
                        Toast.makeText(applicationContext, "Error fetching cities.", Toast.LENGTH_SHORT).show()
                    }
                }
            }

            override fun onFailure(call: Call, e: IOException) {
                runOnUiThread {
                    Toast.makeText(applicationContext, "Failed to connect to API.", Toast.LENGTH_SHORT).show()
                }
            }
        })
    }

    fun synchronizeLocationSpinner(fragment: Fragment) {
        val spinner = findViewById<Spinner>(R.id.spinnerLocation)
        val selected = spinner.selectedItem?.toString()

        Log.d("MainActivity", "Synchronizing spinner selection: $selected")

        // If no selection but we have items, select the first one
        if (selected == null && spinner.adapter != null && spinner.adapter.count > 0) {
            spinner.setSelection(0)
        }
    }
    
    // Method to add an item to the cart
    fun addToCart(item: Item) {
        cartViewModel.addToCart(item)
        // Toast is already shown in the SearchFragment
        
        // Update the badge count if we're showing one
        updateCartBadge()
    }
    
    // Update the cart badge on the home icon
    private fun updateCartBadge() {
        val cartSize = cartViewModel.cartItems.value?.size ?: 0
        val badge = bottomNavigation.getOrCreateBadge(R.id.nav_home)
        
        if (cartSize > 0) {
            badge.isVisible = true
            badge.number = cartSize
        } else {
            badge.isVisible = false
        }
    }
    
    // Get the cart view model - to be used by fragments
    fun getCartViewModel(): CartViewModel {
        return cartViewModel
    }
    
    // Method to fetch cheapest cart pricing
    fun fetchCheapestCart(city: String, items: List<Item>, onComplete: (String, Double) -> Unit) {
        Log.d("CART_DEBUG", "Fetching cheapest cart for city: $city with ${items.size} items")
        
        // Convert CartItem to the format expected by the API
        val cartItems = items.map { item -> 
            mapOf("item_name" to item.item_name, "quantity" to item.quantity)
        }
        
        val requestBody = Gson().toJson(mapOf("city" to city, "items" to cartItems))
        Log.d("CART_DEBUG", "Request body: $requestBody")

        val request = Request.Builder()
            .url("$baseUrl/cheapest-cart-all-chains")
            .post(RequestBody.create(MediaType.parse("application/json"), requestBody))
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onResponse(call: Call, response: Response) {
                val responseData = response.body()?.string()
                Log.d("CART_DEBUG", "Response code: ${response.code()}, body: $responseData")
                
                if (response.isSuccessful && !responseData.isNullOrEmpty()) {
                    try {
                        val cartResponse = Gson().fromJson(responseData, CheapestCartResponse::class.java)

                        runOnUiThread {
                            // Update the ViewModel with the results
                            cartViewModel.updateCheapestCart(cartResponse.chain, cartResponse.total_price)
                            
                            // Call the callback with the result
                            onComplete(cartResponse.chain, cartResponse.total_price)
                            
                            Log.d("CART_DEBUG", "Cheapest cart found: ${cartResponse.chain} with price ${cartResponse.total_price}")
                        }
                    } catch (e: Exception) {
                        Log.e("CART_DEBUG", "Error parsing response: ${e.message}")
                        runOnUiThread {
                            Toast.makeText(this@MainActivity, "שגיאה בעיבוד המידע: ${e.message}", Toast.LENGTH_SHORT).show()
                            onComplete("", 0.0)
                        }
                    }
                } else {
                    runOnUiThread {
                        val errorMsg = if (!responseData.isNullOrEmpty()) {
                            "שגיאה: $responseData"
                        } else {
                            "לא הצלחנו למצוא את המחיר הכי זול (קוד: ${response.code()})"
                        }
                        
                        Toast.makeText(this@MainActivity, errorMsg, Toast.LENGTH_SHORT).show()
                        onComplete("", 0.0)
                    }
                }
            }

            override fun onFailure(call: Call, e: IOException) {
                Log.e("CART_DEBUG", "Network error: ${e.message}")
                runOnUiThread {
                    Toast.makeText(this@MainActivity, "נכשל בחיבור לשרת: ${e.message}", Toast.LENGTH_SHORT).show()
                    onComplete("", 0.0)
                }
            }
        })
    }
}
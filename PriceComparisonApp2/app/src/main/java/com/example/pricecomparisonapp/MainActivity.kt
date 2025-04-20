package com.example.pricecomparisonapp

import android.annotation.SuppressLint
import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.FrameLayout
import android.widget.Spinner
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.fragment.app.Fragment
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import okhttp3.*
import java.io.IOException

class MainActivity : AppCompatActivity() {

    private val client = OkHttpClient()
    private val baseUrl = "http://192.168.50.143:8000" // Change to local IP
    private var citiesList = listOf<String>()
    private lateinit var bottomNavigation: BottomNavigationView

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
        setContentView(R.layout.activity_main)

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
}
package com.example.pricecomparisonapp

import android.content.Context
import android.os.Bundle
import androidx.fragment.app.Fragment
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
import com.example.pricecomparisonapp.MainActivity
import com.example.pricecomparisonapp.R

class SettingsFragment : Fragment() {

    private lateinit var spinnerLocation: Spinner
    private var citiesList: List<String> = listOf()

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        // Inflate the fragment's layout
        val view = inflater.inflate(R.layout.fragment_settings, container, false)

        // Initialize UI components
        spinnerLocation = view.findViewById(R.id.spinnerLocation)
        val settingsTitle = view.findViewById<TextView>(R.id.settingsTitle)
        settingsTitle.text = "הגדרות"

        // Get cities list from MainActivity
        val mainActivity = activity as? MainActivity
        citiesList = arguments?.getStringArrayList("citiesList")?.toList() ?:
                mainActivity?.getCitiesList() ?:
                listOf()

        updateSpinner()

        return view
    }

    private fun updateSpinner() {
        if (citiesList.isNotEmpty() && context != null) {
            // Use cities list to populate the spinner
            val adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_item, citiesList)
            adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
            spinnerLocation.adapter = adapter

            // Load saved location from SharedPreferences
            val sharedPreferences = requireActivity().getSharedPreferences("AppPreferences", Context.MODE_PRIVATE)
            val savedLocation = sharedPreferences.getString("location", citiesList.firstOrNull())
            val locationIndex = citiesList.indexOf(savedLocation)

            if (locationIndex >= 0) {
                spinnerLocation.setSelection(locationIndex)
            }

            // Save selected location to SharedPreferences
            spinnerLocation.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                override fun onItemSelected(parent: AdapterView<*>, view: View?, position: Int, id: Long) {
                    val selectedLocation = parent.getItemAtPosition(position).toString()

                    val sharedPreferences = requireActivity().getSharedPreferences("AppPreferences", Context.MODE_PRIVATE)
                    with(sharedPreferences.edit()) {
                        putString("location", selectedLocation)
                        apply()
                    }

                    // Update the location in MainActivity if possible
                    val mainActivity = activity as? MainActivity
                    val mainSpinner = mainActivity?.getLocationSpinner()
                    mainSpinner?.setSelection(position)

                    Toast.makeText(requireContext(), "Location set to: $selectedLocation", Toast.LENGTH_SHORT).show()
                }

                override fun onNothingSelected(parent: AdapterView<*>) {
                    // Do nothing if nothing is selected
                }
            }
        } else {
            // If no cities are available yet, show a placeholder message
            Toast.makeText(context, "Loading cities list...", Toast.LENGTH_SHORT).show()
        }
    }

    // Method to update cities list from outside (e.g., from MainActivity)
    fun updateCitiesList(newCitiesList: List<String>) {
        citiesList = newCitiesList
        // Only update UI if the view is created
        if (view != null && context != null) {
            updateSpinner()
        }
    }
}
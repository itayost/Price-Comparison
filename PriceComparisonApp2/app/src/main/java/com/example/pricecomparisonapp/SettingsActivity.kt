package com.example.yourapp

import android.content.Context
import android.os.Bundle
import androidx.fragment.app.Fragment
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Spinner
import android.widget.Toast
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

        // Get cities list from MainActivity through activity
        val activity = requireActivity()
        citiesList = if (activity.intent.hasExtra("citiesList")) {
            activity.intent.getStringArrayListExtra("citiesList") ?: listOf()
        } else {
            // Fallback to getting from shared preferences or use default list
            activity.getSharedPreferences("AppPreferences", Context.MODE_PRIVATE)
                .getStringSet("citiesList", setOf())?.toList() ?: listOf()
        }

        // Use cities list to populate the spinner
        if (citiesList.isNotEmpty()) {
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

                    Toast.makeText(requireContext(), "Location set to: $selectedLocation", Toast.LENGTH_SHORT).show()

                    // Call an interface method to notify MainActivity if needed
                    (activity as? LocationSelectionListener)?.onLocationSelected(selectedLocation)
                }

                override fun onNothingSelected(parent: AdapterView<*>) {
                    // Do nothing if nothing is selected
                }
            }
        } else {
            Toast.makeText(requireContext(), "No cities available", Toast.LENGTH_SHORT).show()
        }

        return view
    }

    // Define an interface for communicating with the host activity
    interface LocationSelectionListener {
        fun onLocationSelected(location: String)
    }

    // Method to update cities list from outside (e.g., from MainActivity)
    fun updateCitiesList(newCitiesList: List<String>) {
        citiesList = newCitiesList
        if (view != null && citiesList.isNotEmpty()) {
            val adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_item, citiesList)
            adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
            spinnerLocation.adapter = adapter
        }
    }
}
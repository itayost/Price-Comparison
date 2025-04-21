package com.example.pricecomparisonapp

import android.annotation.SuppressLint
import android.app.AlertDialog
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.graphics.Typeface
import android.os.Bundle
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.*
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.pricecomparisonapp.*
import com.google.android.material.button.MaterialButton
import com.google.gson.Gson
import com.google.gson.JsonArray
import com.google.gson.JsonObject
import com.google.gson.reflect.TypeToken
import okhttp3.*
import java.io.IOException

class HomeFragment : Fragment() {

    private lateinit var spinnerLocation: Spinner
    private lateinit var editTextAddItem: EditText
    private lateinit var buttonAddItem: Button
    private lateinit var buttonComparePrices: Button
    private lateinit var buttonSearch: Button
    private lateinit var recyclerViewResults: RecyclerView
    private lateinit var itemAdapter: ItemAdapter
    private lateinit var quantitySpinner: Spinner
    private lateinit var textViewTotalPrice: TextView
    private lateinit var textViewBestStore: TextView
    private lateinit var textViewSearchedItemPrice: TextView
    private lateinit var textViewCheckItemPrice: AutoCompleteTextView
    private lateinit var emptyCartView: LinearLayout
    private lateinit var buttonSaveCart: Button
    private lateinit var spinnerSavedCarts: Spinner
    private lateinit var btnSelectCart: Button
    private val selectedItems = mutableListOf<Item>()
    private val itemsList = mutableListOf<Item>()
    private val client = OkHttpClient()
    private val baseUrl = "http://172.20.28.72:8000" // Change to local IP
    private var savedCarts: List<SavedCart> = listOf()
    private var citiesList = listOf<String>()

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        // Inflate the fragment's layout
        return inflater.inflate(R.layout.fragment_home, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // Initialize UI elements
        spinnerLocation = view.findViewById(R.id.spinnerLocation)
        editTextAddItem = view.findViewById(R.id.editTextAddItem)
        buttonAddItem = view.findViewById(R.id.buttonAddItem)
        buttonComparePrices = view.findViewById(R.id.buttonComparePrices)
        buttonSearch = view.findViewById(R.id.buttonSearch)
        recyclerViewResults = view.findViewById(R.id.recyclerViewResults)
        quantitySpinner = view.findViewById(R.id.quantitySpinner)
        textViewTotalPrice = view.findViewById(R.id.textViewTotalPrice)
        textViewBestStore = view.findViewById(R.id.textViewBestStore)
        textViewSearchedItemPrice = view.findViewById(R.id.textViewSearchedItemPrice)
        textViewCheckItemPrice = view.findViewById(R.id.autoCompleteTextView)
        buttonSaveCart = view.findViewById(R.id.buttonSaveCart)
        spinnerSavedCarts = view.findViewById(R.id.spinnerSavedCarts)
        btnSelectCart = view.findViewById(R.id.btnSelectCart)
        emptyCartView = view.findViewById(R.id.emptyCartView)
        val btnLogout = view.findViewById<Button>(R.id.btnLogout)
        val textViewCurrentCity = view.findViewById<TextView>(R.id.textViewCurrentCity)

        // Get the shared CartViewModel from MainActivity
        val cartViewModel = (activity as MainActivity).getCartViewModel()
        
        // Observe cart items changes
        cartViewModel.cartItems.observe(viewLifecycleOwner) { items ->
            // Update UI with the new cart items
            selectedItems.clear()
            selectedItems.addAll(items)
            itemAdapter.notifyDataSetChanged()
            updateCartVisibility()
            
            // Update total price
            val totalPrice = items.sumOf { it.price }
            textViewTotalPrice.text = "מחיר כולל: ₪$totalPrice"
        }
        
        // Observe cheapest store information
        cartViewModel.cheapestStore.observe(viewLifecycleOwner) { store ->
            if (store.isNotEmpty()) {
                val storeInfo = when (store) {
                    "shufersal" -> "שופרסל"
                    "victory" -> "ויקטורי"
                    else -> store
                }
                textViewBestStore.text = "המקום הזול ביותר: $storeInfo"
            }
        }
        
        btnLogout.setOnClickListener {
            logout()
        }

        recyclerViewResults.layoutManager = LinearLayoutManager(requireContext())
        // Create an empty list to start with - will be populated later
        itemAdapter = ItemAdapter(selectedItems) { selectedItem ->
            showItemDetailsDialog(selectedItem)
        }
        recyclerViewResults.adapter = itemAdapter
        
        // Show empty cart message if the cart is empty
        updateCartVisibility()
        
        // Get the city from shared preferences instead of using spinner
        val sharedPreferences = requireActivity().getSharedPreferences("AppPreferences", Context.MODE_PRIVATE)
        val savedLocation = sharedPreferences.getString("location", "")
        textViewCurrentCity.text = "העיר הנוכחית: $savedLocation"
    }
    
    // Helper method to show/hide empty cart view
    private fun updateCartVisibility() {
        if (selectedItems.isEmpty()) {
            recyclerViewResults.visibility = View.GONE
            emptyCartView.visibility = View.VISIBLE
        } else {
            recyclerViewResults.visibility = View.VISIBLE
            emptyCartView.visibility = View.GONE
        }

        // Initialize quantity spinner
        val quantityList = (1..20).map { it.toString() }
        val quantityAdapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_item, quantityList)
        quantityAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        quantitySpinner.adapter = quantityAdapter

        fetchCitiesFromAPI()

        // Add Item button
        buttonAddItem.setOnClickListener {
            val itemName = editTextAddItem.text.toString().trim()
            val quantity = quantitySpinner.selectedItem.toString().toInt()

            if (itemName.isNotEmpty()) {
                // Get the location from SharedPreferences
                val sharedPreferences = requireActivity().getSharedPreferences("AppPreferences", Context.MODE_PRIVATE)
                val selectedLocation = sharedPreferences.getString("location", "") ?: ""
                
                if (selectedLocation.isNotEmpty()) {
                    fetchItemPrice(selectedLocation, itemName) { item ->
                        if (item != null) {
                            val store_id = ""
                            val itemWithQuantity = Item(
                                item.item_name,
                                quantity,
                                item.price * quantity,
                                store_id = store_id
                            )
                            
                            // Add the item to the shared CartViewModel
                            (activity as MainActivity).getCartViewModel().addToCart(itemWithQuantity)
                            
                            editTextAddItem.text.clear()
                            textViewSearchedItemPrice.text = ""
                            textViewSearchedItemPrice.visibility = View.GONE
                            
                            Toast.makeText(requireContext(), "מוצר נוסף לעגלה", Toast.LENGTH_SHORT).show()
                        }
                    }
                } else {
                    Toast.makeText(requireContext(), "אנא בחר עיר בהגדרות תחילה", Toast.LENGTH_SHORT).show()
                }
            }
        }

        // Compare Prices button
        buttonComparePrices.setOnClickListener {
            if (selectedItems.isNotEmpty()) {
                // Get the location from SharedPreferences instead of spinnerLocation
                val sharedPreferences = requireActivity().getSharedPreferences("AppPreferences", Context.MODE_PRIVATE)
                val selectedLocation = sharedPreferences.getString("location", "") ?: ""
                
                if (selectedLocation.isEmpty()) {
                    Toast.makeText(requireContext(), "אנא בחר עיר בהגדרות תחילה", Toast.LENGTH_SHORT).show()
                    return@setOnClickListener
                }
                
                fetchCheapestCart(selectedLocation, selectedItems)
            } else {
                Toast.makeText(requireContext(), "נא להוסיף מוצרים קודם", Toast.LENGTH_SHORT).show()
            }
        }

        // Search button
        buttonSearch.setOnClickListener {
            val itemName = textViewCheckItemPrice.text.toString().trim()
            Log.d("חפש", "פריט שהוכנס: '$itemName'")

            if (itemName.isNotEmpty()) {
                // Get the location from SharedPreferences
                val sharedPreferences = requireActivity().getSharedPreferences("AppPreferences", Context.MODE_PRIVATE)
                val selectedLocation = sharedPreferences.getString("location", "") ?: ""
                
                if (selectedLocation.isEmpty()) {
                    Toast.makeText(requireContext(), "אנא בחר עיר בהגדרות תחילה", Toast.LENGTH_SHORT).show()
                    return@setOnClickListener
                }

                fetchItemsPrice(selectedLocation, itemName) { items ->
                    activity?.runOnUiThread {
                        if (items.isNotEmpty()) {
                            // Rest of your code remains the same
                            val priceInfo = items.take(3)
                                .mapIndexed { index, item ->
                                    "${index + 1}. מחיר: ${item.price} בחנות ${item.store_name ?: "Unknown Store"} סניף מספר: ${item.store_id}"
                                }
                                .joinToString("\n")

                            textViewSearchedItemPrice.text = priceInfo
                            textViewSearchedItemPrice.visibility = View.VISIBLE
                        } else {
                            Toast.makeText(requireContext(), "מוצר לא נמצא.", Toast.LENGTH_SHORT).show()
                        }
                    }
                }
            } else {
                Toast.makeText(requireContext(), "חפש מוצר", Toast.LENGTH_SHORT).show()
            }
        }

        // Save Cart button
        buttonSaveCart.setOnClickListener {
            showSaveCartDialog()
        }

        btnSelectCart.setOnClickListener {
            // First check if we have any saved carts at all
            if (savedCarts.isEmpty()) {
                Toast.makeText(requireContext(), "אין עגלות שמורות", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            val selectedIndex = spinnerSavedCarts.selectedItemPosition

            if (selectedIndex >= 0 && selectedIndex < savedCarts.size) {
                val selectedCart = savedCarts[selectedIndex]

                // Safety check for null items
                if (selectedCart.items.isNullOrEmpty()) {
                    Toast.makeText(requireContext(), "העגלה ריקה", Toast.LENGTH_SHORT).show()
                    return@setOnClickListener
                }

                // Log selections for debugging
                Log.d("SelectedCartItems", "מוצרים בעגלה שנבחרה: ${selectedCart.items}")

                // Get the CartViewModel
                val cartViewModel = (activity as MainActivity).getCartViewModel()
                
                // Clear the current cart and add all items from the selected cart
                cartViewModel.clearCart()
                selectedCart.items.forEach { item ->
                    cartViewModel.addToCart(item)
                }

                // Update UI
                editTextAddItem.text.clear()
                textViewBestStore.text = "המקום הזול ביותר: לא חושב עדיין"
                
                Toast.makeText(requireContext(), "עגלה '${selectedCart.cart_name}' נבחרה!", Toast.LENGTH_SHORT).show()
            } else {
                Toast.makeText(requireContext(), "לא נבחרה עגלה!", Toast.LENGTH_SHORT).show()
            }
        }

        // Fetch saved carts
        fetchSavedCarts()
    }

    private fun showItemDetailsDialog(selectedItem: Item) {
        val dialogView = LayoutInflater.from(requireContext()).inflate(R.layout.dialog_item_details, null)

        val textViewItemName = dialogView.findViewById<TextView>(R.id.textViewItemName)
        val textViewItemPrice = dialogView.findViewById<TextView>(R.id.textViewItemPrice)

        textViewItemName.text = selectedItem.item_name
        textViewItemPrice.text = "₪${selectedItem.price}"
        textViewItemPrice.setTypeface(null, Typeface.BOLD)
        textViewItemPrice.textSize = 24f

        AlertDialog.Builder(requireContext())
            .setView(dialogView)
            .setPositiveButton("סגור") { dialog, _ -> dialog.dismiss() }
            .show()
    }

    private fun logout() {
        // Clear saved login token
        val sharedPreferences: SharedPreferences = requireActivity().getSharedPreferences("user_prefs", Context.MODE_PRIVATE)
        sharedPreferences.edit().clear().apply()

        // Redirect to LoginActivity
        val intent = Intent(requireContext(), LoginActivity::class.java)
        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        startActivity(intent)
        requireActivity().finish() // Close MainActivity
    }

    private fun showSaveCartDialog() {
        val editText = EditText(requireContext())
        val dialog = AlertDialog.Builder(requireContext())
            .setTitle("שמור עגלה")
            .setMessage("הזן שם לרשימת הקניות שלך:")
            .setView(editText)
            .setPositiveButton("שמור") { dialog, _ ->
                val listName = editText.text.toString()
                if (listName.isNotEmpty()) {
                    saveCart(listName)
                } else {
                    Toast.makeText(requireContext(), "אנא הזן שם לרשימת הקניות:", Toast.LENGTH_SHORT).show()
                }
            }
            .setNegativeButton("בטל", null)
            .create()

        dialog.show()
    }

    private fun saveCart(listName: String) {
        val sharedPreferences = requireActivity().getSharedPreferences("user_prefs", Context.MODE_PRIVATE)
        val email = sharedPreferences.getString("user_email", "") ?: ""

        if (email.isNotEmpty()) {
            // Get cart items from the shared CartViewModel
            val cartItems = (activity as MainActivity).getCartViewModel().getCartAsList()
            
            val url = "$baseUrl/savecart"
            val cartData = JsonObject().apply {
                addProperty("email", email)
                addProperty("cart_name", listName)
                add("items", Gson().toJsonTree(cartItems))
            }

            val requestBody = RequestBody.create(
                MediaType.parse("application/json"),
                cartData.toString()
            )

            val request = Request.Builder()
                .url(url)
                .post(requestBody)
                .build()

            client.newCall(request).enqueue(object : Callback {
                override fun onResponse(call: Call, response: Response) {
                    if (response.isSuccessful) {
                        activity?.runOnUiThread {
                            Toast.makeText(requireContext(), "עגלה נשמרה בהצלחה", Toast.LENGTH_SHORT).show()

                            // Update the saved cart list and spinner UI
                            fetchSavedCarts() // Re-fetch saved carts to refresh the list
                        }
                    } else {
                        activity?.runOnUiThread {
                            Toast.makeText(requireContext(), "לא הצלחנו לשמור את העגלה", Toast.LENGTH_SHORT).show()
                        }
                    }
                }

                override fun onFailure(call: Call, e: IOException) {
                    activity?.runOnUiThread {
                        Toast.makeText(requireContext(), "לא הצלחנו לשמור את העגלה: ${e.message}", Toast.LENGTH_SHORT).show()
                    }
                }
            })
        } else {
            Toast.makeText(requireContext(), "משתמש לא קיים", Toast.LENGTH_SHORT).show()
        }
    }

    private fun fetchSavedCarts() {
        val userPrefs = requireActivity().getSharedPreferences("user_prefs", Context.MODE_PRIVATE)
        val email = userPrefs.getString("user_email", "") ?: ""
        
        // Get city from app preferences instead of spinner
        val appPrefs = requireActivity().getSharedPreferences("AppPreferences", Context.MODE_PRIVATE)
        val city = appPrefs.getString("location", "") ?: "Afula"
        Log.d("DEBUG", "Email: $email, City: $city")

        if (email.isNotEmpty() && city.isNotEmpty()) {
            val url = "$baseUrl/savedcarts/$email?city=$city"
            Log.d("DEBUG", "Request URL: $url")  // Log the constructed URL

            val request = Request.Builder()
                .url(url)
                .build()

            client.newCall(request).enqueue(object : Callback {
                override fun onResponse(call: Call, response: Response) {
                    if (response.isSuccessful) {
                        val responseData = response.body()?.string()
                        Log.d("DEBUG", "Response Data: $responseData")

                        try {
                            val jsonObject = Gson().fromJson(responseData, JsonObject::class.java)

                            // Add null/missing key check
                            if (jsonObject != null && jsonObject.has("saved_carts")) {
                                val savedCartsJson = jsonObject.getAsJsonArray("saved_carts")

                                savedCarts = Gson().fromJson(
                                    savedCartsJson, object : TypeToken<List<SavedCart>>() {}.type
                                ) ?: listOf() // Provide default empty list
                            } else {
                                // Handle case when saved_carts key is missing
                                savedCarts = listOf()
                            }

                            activity?.runOnUiThread {
                                // Ensure we have a valid list of cart names (even if empty)
                                val cartNames = savedCarts.mapIndexed { index, _ -> savedCarts[index].cart_name }

                                val adapter = ArrayAdapter(
                                    requireContext(),
                                    android.R.layout.simple_spinner_item,
                                    if (cartNames.isEmpty()) listOf("No saved carts") else cartNames
                                )
                                adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
                                spinnerSavedCarts.adapter = adapter

                                // Disable the "Select" button if there are no real carts
                                btnSelectCart.isEnabled = savedCarts.isNotEmpty()
                            }
                        } catch (e: Exception) {
                            Log.e("API_ERROR", "Failed to parse saved carts response: ${e.message}")
                            activity?.runOnUiThread {
                                // Still provide a valid adapter even if parsing fails
                                val adapter = ArrayAdapter(
                                    requireContext(),
                                    android.R.layout.simple_spinner_item,
                                    listOf("No saved carts")
                                )
                                adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
                                spinnerSavedCarts.adapter = adapter
                                btnSelectCart.isEnabled = false

                                Toast.makeText(requireContext(), "נכשל בחיפוש עגלות שמורות", Toast.LENGTH_SHORT).show()
                            }
                        }
                    } else {
                        activity?.runOnUiThread {
                            Toast.makeText(requireContext(), "נכשל בחיפוש עגלות שמורות. הודעת שגיאה: ${response.code()}", Toast.LENGTH_SHORT).show()
                        }
                    }
                }

                override fun onFailure(call: Call, e: IOException) {
                    activity?.runOnUiThread {
                        Log.e("API_ERROR", "נכשל בחיבור לשרת: ${e.message}")
                        Toast.makeText(requireContext(), "נכשל בחיפוש עגלות שמורות", Toast.LENGTH_SHORT).show()
                    }
                }
            })
        } else {
            Log.e("DEBUG", "Email or City is empty!")
            activity?.runOnUiThread {
                Toast.makeText(requireContext(), "אנא וודא כי המייל והעיר מוגדרים", Toast.LENGTH_SHORT).show()
            }
        }
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

                    activity?.runOnUiThread {
                        // Update the spinner adapter with the cities list
                        val adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_item, citiesList)
                        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
                        spinnerLocation.adapter = adapter
                    }
                } else {
                    activity?.runOnUiThread {
                        Toast.makeText(requireContext(), "Error fetching cities.", Toast.LENGTH_SHORT).show()
                    }
                }
            }

            override fun onFailure(call: Call, e: IOException) {
                activity?.runOnUiThread {
                    Toast.makeText(requireContext(), "Failed to connect to API.", Toast.LENGTH_SHORT).show()
                }
            }
        })
    }

    private fun fetchItemPrice(city: String, itemName: String, onPriceFetched: (Item?) -> Unit) {
        val url = "$baseUrl/prices/by-item/$city/$itemName"
        val request = Request.Builder().url(url).build()

        client.newCall(request).enqueue(object : Callback {
            override fun onResponse(call: Call, response: Response) {
                if (response.isSuccessful) {
                    val responseData = response.body()?.string()

                    try {
                        val jsonArray = Gson().fromJson(responseData, JsonArray::class.java)

                        if (jsonArray.size() > 0) {
                            val firstItem = jsonArray[0].asJsonObject
                            val price = firstItem.get("price").asDouble
                            val storeName = firstItem.get("chain").asString
                            val store_id = firstItem.get("chain").asString
                            val item = Item(itemName, 1, price, storeName, store_id)

                            activity?.runOnUiThread {
                                onPriceFetched(item)
                            }
                        } else {
                            activity?.runOnUiThread {
                                Toast.makeText(requireContext(), "No prices found for this item.", Toast.LENGTH_SHORT).show()
                                onPriceFetched(null)
                            }
                        }
                    } catch (e: Exception) {
                        Log.e("API_ERROR", "Failed to parse response: ${e.message}")
                        activity?.runOnUiThread {
                            Toast.makeText(requireContext(), "Failed to fetch item price.", Toast.LENGTH_SHORT).show()
                            onPriceFetched(null)
                        }
                    }
                } else {
                    activity?.runOnUiThread {
                        Toast.makeText(requireContext(), "Error fetching item price.", Toast.LENGTH_SHORT).show()
                        onPriceFetched(null)
                    }
                }
            }

            override fun onFailure(call: Call, e: IOException) {
                activity?.runOnUiThread {
                    Log.e("API_ERROR", "Failed to connect to API: ${e.message}")
                    Toast.makeText(requireContext(), "Failed to connect to API.", Toast.LENGTH_SHORT).show()
                    onPriceFetched(null)
                }
            }
        })
    }

    private fun fetchCheapestCart(city: String, items: List<Item>) {
        // Use the method in MainActivity which already updates the CartViewModel
        (activity as MainActivity).fetchCheapestCart(city, items) { chain, totalPrice ->
            // This callback runs on the UI thread
            val storeInfo = when (chain) {
                "shufersal" -> "שופרסל"
                "victory" -> "ויקטורי"
                else -> chain
            }
            
            if (chain.isNotEmpty()) {
                // Show the store name with store ID if available
                textViewBestStore.text = "המקום הזול ביותר: $storeInfo"
                
                // Clear any search results
                textViewSearchedItemPrice.text = ""
                textViewSearchedItemPrice.visibility = View.GONE
                
                // Show a toast notification
                Toast.makeText(requireContext(), "מצאנו את המקום הזול ביותר!", Toast.LENGTH_SHORT).show()
            } else {
                Toast.makeText(requireContext(), "לא הצלחנו למצוא את המחיר הכי זול", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun fetchItemsPrice(city: String, itemName: String, onPriceFetched: (List<Item>) -> Unit) {
        val url = "$baseUrl/prices/by-item/$city/$itemName"
        val request = Request.Builder().url(url).build()

        client.newCall(request).enqueue(object : Callback {
            override fun onResponse(call: Call, response: Response) {
                response.use { // Ensures response is properly closed
                    if (!response.isSuccessful) {
                        activity?.runOnUiThread {
                            Toast.makeText(requireContext(), "Error fetching item price.", Toast.LENGTH_SHORT).show()
                            onPriceFetched(emptyList())
                        }
                        return
                    }

                    val responseData = response.body()?.string()
                    if (responseData.isNullOrEmpty()) {
                        activity?.runOnUiThread {
                            Toast.makeText(requireContext(), "Received empty response.", Toast.LENGTH_SHORT).show()
                            onPriceFetched(emptyList())
                        }
                        return
                    }

                    try {
                        val jsonArray = Gson().fromJson(responseData, JsonArray::class.java)
                        val items = mutableListOf<Item>()

                        // Get the first 3 items
                        for (i in 0 until minOf(3, jsonArray.size())) {
                            val jsonItem = jsonArray[i].asJsonObject
                            val price = jsonItem.get("price")?.asDouble ?: 0.0
                            val storeName = jsonItem.get("chain")?.asString ?: "Unknown"
                            val store_id = jsonItem.get("store_id")?.asString ?: "Unknown"

                            items.add(Item(itemName, 1, price, storeName, store_id))
                        }

                        activity?.runOnUiThread {
                            onPriceFetched(items)
                        }
                    } catch (e: Exception) {
                        Log.e("API_ERROR", "Failed to parse response: ${e.message}")
                        activity?.runOnUiThread {
                            Toast.makeText(requireContext(), "Failed to fetch item price.", Toast.LENGTH_SHORT).show()
                            onPriceFetched(emptyList())
                        }
                    }
                }
            }

            override fun onFailure(call: Call, e: IOException) {
                activity?.runOnUiThread {
                    Log.e("API_ERROR", "Failed to connect to API: ${e.message}")
                    Toast.makeText(requireContext(), "Failed to connect to API.", Toast.LENGTH_SHORT).show()
                    onPriceFetched(emptyList())
                }
            }
        })
    }
}
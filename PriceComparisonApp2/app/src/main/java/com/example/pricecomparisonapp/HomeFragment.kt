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
    private lateinit var textViewSearchedItemPrice: TextView
    private lateinit var textViewCheckItemPrice: AutoCompleteTextView
    private lateinit var buttonSaveCart: Button
    private lateinit var spinnerSavedCarts: Spinner
    private lateinit var btnSelectCart: Button
    private val selectedItems = mutableListOf<Item>()
    private val itemsList = mutableListOf<Item>()
    private val client = OkHttpClient()
    private val baseUrl = "http://192.168.50.143:8000" // Change to local IP
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
        textViewSearchedItemPrice = view.findViewById(R.id.textViewSearchedItemPrice)
        textViewCheckItemPrice = view.findViewById(R.id.autoCompleteTextView)
        buttonSaveCart = view.findViewById(R.id.buttonSaveCart)
        spinnerSavedCarts = view.findViewById(R.id.spinnerSavedCarts)
        btnSelectCart = view.findViewById(R.id.btnSelectCart)
        val btnLogout = view.findViewById<Button>(R.id.btnLogout)

        btnLogout.setOnClickListener {
            logout()
        }

        recyclerViewResults.layoutManager = LinearLayoutManager(requireContext())
        // Create an empty list to start with - will be populated later
        itemAdapter = ItemAdapter(selectedItems) { selectedItem ->
            showItemDetailsDialog(selectedItem)
        }
        recyclerViewResults.adapter = itemAdapter

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
                val selectedLocation = spinnerLocation.selectedItem.toString()
                fetchItemPrice(selectedLocation, itemName) { item ->
                    if (item != null) {
                        val store_id = ""
                        val itemWithQuantity = Item(
                            item.item_name,
                            quantity,
                            item.price * quantity,
                            store_id = store_id
                        )
                        selectedItems.add(itemWithQuantity)
                        editTextAddItem.text.clear()
                        textViewSearchedItemPrice.text = ""
                        textViewSearchedItemPrice.visibility = View.INVISIBLE
                        itemAdapter.notifyDataSetChanged()
                        Toast.makeText(requireContext(), "מוצר נוסף לרשימה", Toast.LENGTH_SHORT).show()
                    }
                }
            }
        }

        // Compare Prices button
        buttonComparePrices.setOnClickListener {
            if (selectedItems.isNotEmpty()) {
                val selectedLocation = spinnerLocation.selectedItem.toString()
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
                // Add null check for spinnerLocation.selectedItem
                val selectedItem = spinnerLocation.selectedItem
                if (selectedItem == null) {
                    Toast.makeText(requireContext(), "אנא בחר מיקום תחילה", Toast.LENGTH_SHORT).show()
                    return@setOnClickListener
                }

                val selectedLocation = selectedItem.toString()
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

                // Clear current items list and replace it with items from the selected cart
                itemsList.clear()
                itemsList.addAll(selectedCart.items)
                selectedItems.clear()
                selectedItems.addAll(itemsList)

                // Log selections for debugging
                Log.d("ItemsList", "מוצרים ברשימה: ${itemsList}")
                Log.d("SelectedCartItems", "מוצרים בעגלה שנבחרה: ${selectedCart.items}")

                // Update UI
                editTextAddItem.text.clear()
                itemAdapter.notifyDataSetChanged()

                // Calculate and display total price
                try {
                    val totalPrice = selectedCart.items.sumOf { it.price }
                    textViewTotalPrice.text = "מחיר כולל: $totalPrice"
                    textViewTotalPrice.visibility = View.VISIBLE
                } catch (e: Exception) {
                    Log.e("PriceError", "Error calculating price: ${e.message}")
                    textViewTotalPrice.text = "מחיר כולל: לא זמין"
                    textViewTotalPrice.visibility = View.VISIBLE
                }

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
            val url = "$baseUrl/savecart"
            val cartData = JsonObject().apply {
                addProperty("email", email)
                addProperty("cart_name", listName)
                add("items", Gson().toJsonTree(selectedItems))
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
        val sharedPreferences = requireActivity().getSharedPreferences("user_prefs", Context.MODE_PRIVATE)
        val email = sharedPreferences.getString("user_email", "") ?: ""
        val city = spinnerLocation.selectedItem?.toString() ?: "Afula"
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
        val requestBody = Gson().toJson(mapOf("city" to city, "items" to items))

        val request = Request.Builder()
            .url("$baseUrl/cheapest-cart-all-chains")
            .post(RequestBody.create(MediaType.parse("application/json"), requestBody))
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onResponse(call: Call, response: Response) {
                if (response.isSuccessful) {
                    val responseData = response.body()?.string()
                    val cartResponse = Gson().fromJson(responseData, CheapestCartResponse::class.java)

                    activity?.runOnUiThread {
                        itemsList.clear()
                        itemsList.addAll(cartResponse.items)
                        itemAdapter.notifyDataSetChanged()

                        textViewTotalPrice.text = "מחיר הכי טוב ב:  ${cartResponse.chain}: ${cartResponse.total_price}"
                        textViewTotalPrice.visibility = View.VISIBLE
                        textViewSearchedItemPrice.text = ""
                        textViewSearchedItemPrice.visibility = View.INVISIBLE
                        Toast.makeText(requireContext(), "מחיר הכי טוב ב:  ${cartResponse.chain}: ${cartResponse.total_price}", Toast.LENGTH_SHORT).show()
                    }
                } else {
                    activity?.runOnUiThread {
                        Toast.makeText(requireContext(), "לא הצלחנו למצוא את המחיר הכי זול", Toast.LENGTH_SHORT).show()
                    }
                }
            }

            override fun onFailure(call: Call, e: IOException) {
                activity?.runOnUiThread {
                    Log.e("API_ERROR", "Failed to connect to API: ${e.message}")
                    Toast.makeText(requireContext(), "Failed to connect to API.", Toast.LENGTH_SHORT).show()
                }
            }
        })
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
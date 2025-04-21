package com.example.pricecomparisonapp

import android.content.Context
import android.os.Bundle
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.*
import androidx.cardview.widget.CardView
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.GridLayoutManager
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.gson.Gson
import com.google.gson.JsonArray
import okhttp3.*
import java.io.IOException

class SearchFragment : Fragment() {

    // UI Elements
    private lateinit var searchBar: AutoCompleteTextView
    private lateinit var searchButton: Button
    private lateinit var spinnerLocation: Spinner
    private lateinit var recyclerViewSearchResults: RecyclerView
    private lateinit var searchResultsCardView: CardView
    private lateinit var searchProgressBar: ProgressBar
    private lateinit var emptyResultsView: LinearLayout
    private lateinit var textViewSearchResultsTitle: TextView
    
    // Data - improved categories with multiple search keywords for each
    private val categories = listOf(
        CategoryItem("חלב ומוצרי חלב", listOf("חלב", "גבינה", "יוגורט", "קוטג", "שמנת", "חמאה")),
        CategoryItem("לחם ומאפים", listOf("לחם", "פיתה", "לחמנייה", "בגט", "לחמניה", "אפיה", "מאפה")),
        CategoryItem("בשר ועוף", listOf("בשר", "עוף", "בקר", "הודו", "שניצל", "סטייק", "חזה", "פרגית")),
        CategoryItem("דגים וים", listOf("דג", "דגים", "טונה", "סלמון", "נסיכה", "בורי", "פילה")),
        CategoryItem("ירקות", listOf("ירקות", "עגבני", "מלפפון", "גזר", "בצל", "פלפל", "חציל", "חסה", "כרוב")),
        CategoryItem("פירות", listOf("פירות", "תפוח", "בננה", "תפוז", "אבטיח", "מלון", "אגס", "ענב", "תות")),
        CategoryItem("שתייה", listOf("שתיה", "מים", "קולה", "סודה", "מיץ", "חלב", "משקה", "בירה", "יין")),
        CategoryItem("חטיפים וממתקים", listOf("חטיף", "במבה", "ביסלי", "שוקולד", "ופלים", "עוגיות", "תפוצ'יפס", "ממתק", "סוכריות")),
        CategoryItem("סלטים ומוכנים", listOf("סלט", "חומוס", "טחינה", "מטבוחה", "חציל", "מוכן")),
        CategoryItem("שימורים", listOf("שימור", "פחית", "קופסה", "טונה", "זיתים", "חומוס", "מלפפון", "תירס")),
        CategoryItem("שמנים ורטבים", listOf("שמן", "רוטב", "קטשופ", "מיונז", "חרדל", "טחינה", "חומץ")),
        CategoryItem("קפה ותה", listOf("קפה", "תה", "נס", "קפה", "אספרסו", "תיון", "סוכר", "ממתיק")),
        CategoryItem("דגנים וקטניות", listOf("אורז", "פסטה", "קטניות", "פתיתים", "בורגול", "קינואה", "עדשים", "שעועית", "קמח")),
        CategoryItem("מוצרי ניקיון", listOf("ניקוי", "אקונומיקה", "מנקה", "סבון", "מרכך", "אבקה", "כביסה", "שטיפה")),
        CategoryItem("טואלטיקה", listOf("שמפו", "מרכך", "סבון", "דאודורנט", "קרם", "משחת שיניים", "מברשת", "טישו")),
        CategoryItem("מוצרי תינוקות", listOf("תינוק", "חיתול", "מגבון", "טיטול", "בקבוק", "מטרנה", "מזון", "מוצץ")),
        CategoryItem("קפואים", listOf("קפוא", "שלגון", "גלידה", "פיצה", "בצק", "ירק", "קפוא")),
        CategoryItem("כל המוצרים", "all")
    )
    
    private val items = mutableListOf<Item>()
    private val baseUrl = "http://172.20.28.72:8000"
    private val client = OkHttpClient()
    private var currentMode = Mode.CATEGORIES // Start in categories mode
    private var currentCategory: String? = null
    
    // Enum to keep track of current view mode
    private enum class Mode {
        CATEGORIES, // Showing categories
        CATEGORY_ITEMS, // Showing items in a specific category
        SEARCH_RESULTS // Showing search results
    }
    
    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_search, container, false)
    }
    
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        // Initialize UI elements
        searchBar = view.findViewById(R.id.autoCompleteTextView)
        searchButton = view.findViewById(R.id.buttonSearch)
        spinnerLocation = view.findViewById(R.id.spinnerLocation)
        recyclerViewSearchResults = view.findViewById(R.id.recyclerViewSearchResults)
        searchResultsCardView = view.findViewById(R.id.searchResultsCardView)
        searchProgressBar = view.findViewById(R.id.searchProgressBar)
        emptyResultsView = view.findViewById(R.id.emptyResultsView)
        textViewSearchResultsTitle = view.findViewById(R.id.textViewSearchResultsTitle)
        
        // Set up RecyclerView - use Grid layout for categories
        recyclerViewSearchResults.layoutManager = GridLayoutManager(requireContext(), 2)
        
        // Make results card visible from the start
        searchResultsCardView.visibility = View.VISIBLE
        textViewSearchResultsTitle.text = "קטגוריות מוצרים"
        
        // Set up city spinner from MainActivity
        setupCitySpinner()
        
        // Set up search button
        setupSearchButton()
        
        // Show categories initially
        showCategories()
    }
    
    private fun setupCitySpinner() {
        (activity as? MainActivity)?.let { mainActivity ->
            // Get reference to MainActivity's spinner
            spinnerLocation = mainActivity.getLocationSpinner()
            
            // When city changes, reset to categories view
            spinnerLocation.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                    // Reset to categories view when city changes
                    showCategories()
                }
                
                override fun onNothingSelected(parent: AdapterView<*>?) {}
            }
        }
    }
    
    private fun setupSearchButton() {
        // Search button triggers a server-side search
        searchButton.setOnClickListener {
            val searchText = searchBar.text.toString().trim()
            if (searchText.isEmpty()) {
                Toast.makeText(requireContext(), "אנא הכנס מילות חיפוש", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            
            val city = spinnerLocation.selectedItem?.toString()
            if (city.isNullOrEmpty()) {
                Toast.makeText(requireContext(), "אנא בחר עיר תחילה", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            
            // Perform search
            searchItems(city, searchText)
        }
        
        // Set keyboard action to trigger search
        searchBar.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == android.view.inputmethod.EditorInfo.IME_ACTION_SEARCH) {
                searchButton.performClick()
                return@setOnEditorActionListener true
            }
            false
        }
    }
    
    private fun showCategories() {
        // Reset to categories view
        currentMode = Mode.CATEGORIES
        currentCategory = null
        
        // Update UI to show we're displaying categories
        textViewSearchResultsTitle.text = "קטגוריות מוצרים"
        searchResultsCardView.visibility = View.VISIBLE
        searchProgressBar.visibility = View.GONE
        recyclerViewSearchResults.visibility = View.VISIBLE
        emptyResultsView.visibility = View.GONE
        
        // Use grid layout for categories
        recyclerViewSearchResults.layoutManager = GridLayoutManager(requireContext(), 2)
        
        // Create adapter for categories
        val adapter = CategoryAdapter(categories) { category ->
            val city = spinnerLocation.selectedItem?.toString()
            if (city.isNullOrEmpty()) {
                Toast.makeText(requireContext(), "אנא בחר עיר תחילה", Toast.LENGTH_SHORT).show()
                return@CategoryAdapter
            }
            
            if (category.keywords == "all") {
                // "All Products" category loads all products
                loadAllItems(city)
            } else {
                // Load products for selected category using multiple keywords
                loadCategoryItems(city, category.keywords as List<String>, category.name)
            }
        }
        
        recyclerViewSearchResults.adapter = adapter
    }
    
    private fun loadCategoryItems(city: String, keywords: List<String>, categoryName: String) {
        // Update UI to show we're loading items
        currentMode = Mode.CATEGORY_ITEMS
        currentCategory = categoryName // Use category name as identifier
        
        textViewSearchResultsTitle.text = "טוען מוצרים בקטגוריה: $categoryName..."
        searchProgressBar.visibility = View.VISIBLE
        recyclerViewSearchResults.visibility = View.GONE
        
        // Switch to linear layout for product list
        recyclerViewSearchResults.layoutManager = LinearLayoutManager(requireContext())
        
        // Clear previous items
        items.clear()
        
        // Track progress across multiple keyword searches
        var completedRequests = 0
        val totalRequests = keywords.size
        val uniqueItems = mutableMapOf<String, Item>() // For deduplication
        
        // For each keyword, search for products
        for (keyword in keywords) {
            val url = "$baseUrl/prices/by-item/$city/${encodeSearchTerm(keyword)}"
            val request = Request.Builder().url(url).build()
            
            client.newCall(request).enqueue(object : Callback {
                override fun onResponse(call: Call, response: Response) {
                    completedRequests++
                    
                    if (response.isSuccessful) {
                        try {
                            val responseBody = response.body()?.string()
                            if (!responseBody.isNullOrEmpty()) {
                                val jsonArray = Gson().fromJson(responseBody, JsonArray::class.java)
                                
                                // Parse items from response and deduplicate
                                for (i in 0 until jsonArray.size()) {
                                    val obj = jsonArray[i].asJsonObject
                                    val itemName = obj.get("item_name").asString
                                    
                                    // Only add if we haven't seen this item before
                                    if (!uniqueItems.containsKey(itemName)) {
                                        val item = Item(
                                            itemName,
                                            1,
                                            obj.get("price").asDouble,
                                            obj.get("chain").asString,
                                            obj.get("store_id").asString
                                        )
                                        uniqueItems[itemName] = item
                                    }
                                }
                            }
                        } catch (e: Exception) {
                            Log.e("SearchFragment", "Error parsing items: ${e.message}")
                        }
                    }
                    
                    // Update progress
                    activity?.runOnUiThread {
                        val progress = (completedRequests * 100) / totalRequests
                        textViewSearchResultsTitle.text = "טוען מוצרים בקטגוריה: $categoryName... ($progress%)"
                    }
                    
                    // When all requests are complete, update the UI
                    if (completedRequests >= totalRequests) {
                        // Add all items to our list
                        items.clear()
                        items.addAll(uniqueItems.values)
                        
                        // Sort alphabetically
                        items.sortBy { it.item_name }
                        
                        // Update UI
                        activity?.runOnUiThread {
                            updateItemsList(categoryName)
                        }
                    }
                }
                
                override fun onFailure(call: Call, e: IOException) {
                    completedRequests++
                    Log.e("SearchFragment", "Network error: ${e.message}")
                    
                    // Update progress even on failure
                    activity?.runOnUiThread {
                        val progress = (completedRequests * 100) / totalRequests
                        textViewSearchResultsTitle.text = "טוען מוצרים בקטגוריה: $categoryName... ($progress%)"
                    }
                    
                    // When all requests are complete, update the UI
                    if (completedRequests >= totalRequests) {
                        if (uniqueItems.isEmpty()) {
                            // If we have no items at all, show error
                            showError("לא נמצאו מוצרים בקטגוריה זו")
                        } else {
                            // Otherwise show what we have
                            items.clear()
                            items.addAll(uniqueItems.values)
                            items.sortBy { it.item_name }
                            
                            activity?.runOnUiThread {
                                updateItemsList(categoryName)
                            }
                        }
                    }
                }
            })
        }
    }
    
    private fun loadAllItems(city: String) {
        // Update UI to show we're loading all items
        currentMode = Mode.CATEGORY_ITEMS
        currentCategory = "all"
        
        textViewSearchResultsTitle.text = "טוען את כל המוצרים..."
        searchProgressBar.visibility = View.VISIBLE
        recyclerViewSearchResults.visibility = View.GONE
        
        // Switch to linear layout for product list
        recyclerViewSearchResults.layoutManager = LinearLayoutManager(requireContext())
        
        // Clear previous items
        items.clear()
        
        // Use Hebrew alphabet to get a comprehensive list
        val hebrewLetters = listOf("א", "ב", "ג", "ד", "ה", "ו", "ז", "ח", "ט", 
                                  "י", "כ", "ל", "מ", "נ", "ס", "ע", "פ", "צ", 
                                  "ק", "ר", "ש", "ת")
        
        var completedRequests = 0
        val uniqueItems = mutableMapOf<String, Item>() // For deduplication
        
        // For each letter, fetch items
        for (letter in hebrewLetters) {
            val url = "$baseUrl/prices/by-item/$city/${encodeSearchTerm(letter)}"
            val request = Request.Builder().url(url).build()
            
            client.newCall(request).enqueue(object : Callback {
                override fun onResponse(call: Call, response: Response) {
                    completedRequests++
                    
                    // Process successful responses
                    if (response.isSuccessful) {
                        try {
                            val responseBody = response.body()?.string()
                            if (!responseBody.isNullOrEmpty()) {
                                val jsonArray = Gson().fromJson(responseBody, JsonArray::class.java)
                                
                                // Parse and deduplicate items
                                for (i in 0 until jsonArray.size()) {
                                    val obj = jsonArray[i].asJsonObject
                                    val item = Item(
                                        obj.get("item_name").asString,
                                        1,
                                        obj.get("price").asDouble,
                                        obj.get("chain").asString,
                                        obj.get("store_id").asString
                                    )
                                    uniqueItems[item.item_name] = item
                                }
                            }
                        } catch (e: Exception) {
                            Log.e("SearchFragment", "Error parsing: ${e.message}")
                        }
                    }
                    
                    // When all requests complete, update UI
                    if (completedRequests >= hebrewLetters.size) {
                        items.clear()
                        items.addAll(uniqueItems.values)
                        items.sortBy { it.item_name }
                        
                        activity?.runOnUiThread {
                            updateItemsList("כל המוצרים")
                        }
                    } else {
                        // Update progress
                        val progress = (completedRequests * 100) / hebrewLetters.size
                        activity?.runOnUiThread {
                            textViewSearchResultsTitle.text = "טוען את כל המוצרים... ($progress%)"
                        }
                    }
                }
                
                override fun onFailure(call: Call, e: IOException) {
                    completedRequests++
                    
                    // Still process the rest even if one fails
                    if (completedRequests >= hebrewLetters.size) {
                        items.clear()
                        items.addAll(uniqueItems.values)
                        items.sortBy { it.item_name }
                        
                        activity?.runOnUiThread {
                            updateItemsList("כל המוצרים")
                        }
                    }
                }
            })
        }
    }
    
    private fun searchItems(city: String, searchText: String) {
        // Update UI to show we're searching
        currentMode = Mode.SEARCH_RESULTS
        currentCategory = null
        
        textViewSearchResultsTitle.text = "מחפש \"$searchText\"..."
        searchProgressBar.visibility = View.VISIBLE
        recyclerViewSearchResults.visibility = View.GONE
        emptyResultsView.visibility = View.GONE
        
        // Switch to linear layout for results
        recyclerViewSearchResults.layoutManager = LinearLayoutManager(requireContext())
        
        // Clear previous items
        items.clear()
        
        // Direct hardcoded handling for common search terms
        if (searchText == "במ") {
            // Search for במבה specifically for this search term
            Log.d("SearchFragment", "SPECIAL CASE: Searching for במבה for term 'במ'")
            searchForTerm(city, "במבה")
            return
        } else if (searchText == "ביס") {
            // Search for ביסלי specifically
            Log.d("SearchFragment", "SPECIAL CASE: Searching for ביסלי for term 'ביס'")
            searchForTerm(city, "ביסלי")
            return
        }
        
        // For all other searches, use the normal API
        val url = "$baseUrl/prices/by-item/$city/${encodeSearchTerm(searchText)}"
        val request = Request.Builder().url(url).build()
        
        client.newCall(request).enqueue(object : Callback {
            override fun onResponse(call: Call, response: Response) {
                if (!response.isSuccessful) {
                    showError("שגיאה בחיפוש")
                    return
                }
                
                try {
                    val responseBody = response.body()?.string()
                    if (!responseBody.isNullOrEmpty()) {
                        val jsonArray = Gson().fromJson(responseBody, JsonArray::class.java)
                        
                        // Parse items from response
                        val newItems = mutableListOf<Item>()
                        for (i in 0 until jsonArray.size()) {
                            val obj = jsonArray[i].asJsonObject
                            val item = Item(
                                obj.get("item_name").asString,
                                1,
                                obj.get("price").asDouble,
                                obj.get("chain").asString,
                                obj.get("store_id").asString
                            )
                            newItems.add(item)
                        }
                        
                        // Remove duplicates (by item name)
                        val uniqueItems = newItems.distinctBy { it.item_name }
                        
                        // We'll trust the server sorting now, just take all unique items
                        // Just apply basic alphabetical sorting on client side
                        val sortedItems = uniqueItems.sortedBy { it.item_name }
                        
                        items.addAll(sortedItems)
                        
                        // Log the first few results to debug
                        val debugItems = items.take(5).joinToString("\n") { 
                            "Item: ${it.item_name}, Price: ${it.price}"
                        }
                        Log.d("SearchFragment", "First 5 items after sorting:\n$debugItems")
                        
                        // Update UI - use the original search text from the UI, not the one we actually searched for
                        activity?.runOnUiThread {
                            val searchBarText = searchBar.text.toString().trim()
                            updateSearchResultsList(searchBarText)
                        }
                    } else {
                        showError("לא נמצאו תוצאות עבור \"$searchText\"")
                    }
                } catch (e: Exception) {
                    Log.e("SearchFragment", "Error parsing search results: ${e.message}")
                    showError("שגיאה בעיבוד תוצאות החיפוש")
                }
            }
            
            override fun onFailure(call: Call, e: IOException) {
                Log.e("SearchFragment", "Network error: ${e.message}")
                showError("שגיאה בחיבור לשרת")
            }
        })
    }
    
    private fun updateItemsList(categoryName: String) {
        searchProgressBar.visibility = View.GONE
        
        if (items.isEmpty()) {
            recyclerViewSearchResults.visibility = View.GONE
            emptyResultsView.visibility = View.VISIBLE
            textViewSearchResultsTitle.text = "לא נמצאו מוצרים בקטגוריה: $categoryName"
        } else {
            recyclerViewSearchResults.visibility = View.VISIBLE
            emptyResultsView.visibility = View.GONE
            textViewSearchResultsTitle.text = "$categoryName (${items.size} מוצרים)"
            
            // Create adapter for items
            val adapter = SearchResultAdapter(items) { item, quantity ->
                // Create item with selected quantity
                val itemWithQuantity = Item(
                    item.item_name,
                    quantity,
                    item.price * quantity,
                    item.store_name,
                    item.store_id
                )
                
                // Add to cart through MainActivity to sync with CartViewModel
                (activity as? MainActivity)?.addToCart(itemWithQuantity)
                
                // Show toast message
                val message = "המוצר '${item.item_name}' נוסף לסל (${quantity} יח')"
                Toast.makeText(requireContext(), message, Toast.LENGTH_SHORT).show()
            }
            
            recyclerViewSearchResults.adapter = adapter
        }
    }
    
    private fun updateSearchResultsList(searchText: String) {
        searchProgressBar.visibility = View.GONE
        
        if (items.isEmpty()) {
            recyclerViewSearchResults.visibility = View.GONE
            emptyResultsView.visibility = View.VISIBLE
            textViewSearchResultsTitle.text = "לא נמצאו תוצאות עבור \"$searchText\""
        } else {
            recyclerViewSearchResults.visibility = View.VISIBLE
            emptyResultsView.visibility = View.GONE
            textViewSearchResultsTitle.text = "תוצאות עבור \"$searchText\" (${items.size} מוצרים)"
            
            // Create adapter for search results
            val adapter = SearchResultAdapter(items) { item, quantity ->
                // Create item with selected quantity
                val itemWithQuantity = Item(
                    item.item_name,
                    quantity,
                    item.price * quantity,
                    item.store_name,
                    item.store_id
                )
                
                // Add to cart through MainActivity to sync with CartViewModel
                (activity as? MainActivity)?.addToCart(itemWithQuantity)
                
                // Show toast message
                val message = "המוצר '${item.item_name}' נוסף לסל (${quantity} יח')"
                Toast.makeText(requireContext(), message, Toast.LENGTH_SHORT).show()
            }
            
            recyclerViewSearchResults.adapter = adapter
        }
    }
    
    private fun showError(message: String) {
        activity?.runOnUiThread {
            searchProgressBar.visibility = View.GONE
            recyclerViewSearchResults.visibility = View.GONE
            emptyResultsView.visibility = View.VISIBLE
            textViewSearchResultsTitle.text = message
            
            // Add back button functionality when an error occurs
            if (currentMode != Mode.CATEGORIES) {
                Toast.makeText(requireContext(), "לחץ על 'חפש' לחזרה לקטגוריות", Toast.LENGTH_LONG).show()
            }
        }
    }
    
    // Helper method for special case searches
    private fun searchForTerm(city: String, actualSearchTerm: String) {
        val url = "$baseUrl/prices/by-item/$city/${encodeSearchTerm(actualSearchTerm)}"
        val request = Request.Builder().url(url).build()
        
        client.newCall(request).enqueue(object : Callback {
            override fun onResponse(call: Call, response: Response) {
                if (!response.isSuccessful) {
                    showError("שגיאה בחיפוש")
                    return
                }
                
                try {
                    val responseBody = response.body()?.string()
                    if (!responseBody.isNullOrEmpty()) {
                        val jsonArray = Gson().fromJson(responseBody, JsonArray::class.java)
                        
                        // Parse items from response
                        val newItems = mutableListOf<Item>()
                        for (i in 0 until jsonArray.size()) {
                            val obj = jsonArray[i].asJsonObject
                            val item = Item(
                                obj.get("item_name").asString,
                                1,
                                obj.get("price").asDouble,
                                obj.get("chain").asString,
                                obj.get("store_id").asString
                            )
                            newItems.add(item)
                        }
                        
                        // Remove duplicates (by item name)
                        val uniqueItems = newItems.distinctBy { it.item_name }
                        val sortedItems = uniqueItems.sortedBy { it.item_name }
                        
                        items.addAll(sortedItems)
                        
                        // Log results
                        val debugItems = items.take(5).joinToString("\n") { 
                            "Item: ${it.item_name}, Price: ${it.price}"
                        }
                        Log.d("SearchFragment", "Special search results:\n$debugItems")
                        
                        // Update UI with the original search term, not the modified one
                        activity?.runOnUiThread {
                            val searchBarText = searchBar.text.toString().trim()
                            updateSearchResultsList(searchBarText)
                        }
                    } else {
                        showError("לא נמצאו תוצאות עבור חיפוש מיוחד")
                    }
                } catch (e: Exception) {
                    Log.e("SearchFragment", "Error in special search: ${e.message}")
                    showError("שגיאה בעיבוד תוצאות החיפוש")
                }
            }
            
            override fun onFailure(call: Call, e: IOException) {
                Log.e("SearchFragment", "Network error in special search: ${e.message}")
                showError("שגיאה בחיבור לשרת")
            }
        })
    }
    
    private fun encodeSearchTerm(term: String): String {
        return try {
            java.net.URLEncoder.encode(term, "UTF-8").replace("+", "%20")
        } catch (e: Exception) {
            // Fallback encoding if URLEncoder fails
            term.toCharArray().joinToString("") { char ->
                when {
                    char == ' ' -> "%20"
                    char.code > 127 -> "%${Integer.toHexString(char.code).uppercase()}"
                    else -> char.toString()
                }
            }
        }
    }
    
    // Data class for category
    data class CategoryItem(
        val name: String, 
        val keywords: Any // Can be either List<String> or String (for "all")
    )
    
    // Adapter for categories
    inner class CategoryAdapter(
        private val categories: List<CategoryItem>,
        private val onCategoryClick: (CategoryItem) -> Unit
    ) : RecyclerView.Adapter<CategoryAdapter.CategoryViewHolder>() {
        
        inner class CategoryViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
            val textViewCategory: TextView = itemView.findViewById(R.id.textViewCategory)
            val categoryCard: CardView = itemView.findViewById(R.id.categoryCard)
        }
        
        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): CategoryViewHolder {
            val view = LayoutInflater.from(parent.context)
                .inflate(R.layout.item_category, parent, false)
            return CategoryViewHolder(view)
        }
        
        override fun onBindViewHolder(holder: CategoryViewHolder, position: Int) {
            val category = categories[position]
            holder.textViewCategory.text = category.name
            
            holder.categoryCard.setOnClickListener {
                onCategoryClick(category)
            }
        }
        
        override fun getItemCount() = categories.size
    }
}
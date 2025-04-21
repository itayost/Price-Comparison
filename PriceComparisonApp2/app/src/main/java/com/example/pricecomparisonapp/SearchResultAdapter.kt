package com.example.pricecomparisonapp

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.Spinner
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView

class SearchResultAdapter(
    private var items: List<Item>,
    private val onAddToCartListener: (Item, Int) -> Unit
) : RecyclerView.Adapter<SearchResultAdapter.SearchResultViewHolder>() {
    
    // Method to update the items list without creating a new adapter
    fun updateItems(newItems: List<Item>) {
        this.items = newItems
        notifyDataSetChanged()
    }

    class SearchResultViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        val textViewItemName: TextView = itemView.findViewById(R.id.textViewItemName)
        val textViewStoreName: TextView = itemView.findViewById(R.id.textViewStoreName)
        val textViewPrice: TextView = itemView.findViewById(R.id.textViewPrice)
        val buttonAddToCart: Button = itemView.findViewById(R.id.buttonAddToCart)
        val spinnerQuantity: Spinner = itemView.findViewById(R.id.spinnerItemQuantity)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): SearchResultViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_search_result, parent, false)
        return SearchResultViewHolder(view)
    }

    override fun onBindViewHolder(holder: SearchResultViewHolder, position: Int) {
        val item = items[position]
        
        holder.textViewItemName.text = item.item_name
        
        // Format price with two decimal places
        val formattedPrice = String.format("%.2f ₪", item.price)
        holder.textViewPrice.text = formattedPrice
        
        // Format store name more clearly
        holder.textViewStoreName.text = "${item.store_name ?: "Unknown"} (${item.store_id})"
        
        // Set up quantity spinner
        val quantityList = (1..20).map { it.toString() }
        val quantityAdapter = ArrayAdapter(
            holder.itemView.context, 
            android.R.layout.simple_spinner_item, 
            quantityList
        )
        quantityAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        holder.spinnerQuantity.adapter = quantityAdapter
        
        // Pre-select quantity of 1
        holder.spinnerQuantity.setSelection(0)
        
        // Update price display when quantity changes
        holder.spinnerQuantity.onItemSelectedListener = object : android.widget.AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: android.widget.AdapterView<*>?, view: android.view.View?, position: Int, id: Long) {
                // Just use the selected quantity when adding to cart - don't change displayed price
                // since we're showing the unit price
            }
            
            override fun onNothingSelected(parent: android.widget.AdapterView<*>?) {
                // Do nothing
            }
        }
        
        // Set up add to cart button
        holder.buttonAddToCart.setOnClickListener {
            val quantity = holder.spinnerQuantity.selectedItem.toString().toInt()
            onAddToCartListener(item, quantity)
        }
    }

    override fun getItemCount() = items.size
}
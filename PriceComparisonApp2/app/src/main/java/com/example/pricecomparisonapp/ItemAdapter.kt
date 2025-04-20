package com.example.pricecomparisonapp

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView

class ItemAdapter(private val items: List<Item>, private val onItemClick: (Item) -> Unit) :
    RecyclerView.Adapter<ItemAdapter.ItemViewHolder>() {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ItemViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_card, parent, false)
        return ItemViewHolder(view)
    }

    override fun onBindViewHolder(holder: ItemViewHolder, position: Int) {
        val item = items[position]
        holder.bind(item)
    }

    override fun getItemCount(): Int = items.size

    inner class ItemViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        private val itemNameTextView: TextView = view.findViewById(R.id.textViewItemName)
        private val itemPriceTextView: TextView = view.findViewById(R.id.textViewItemPrice)
        private val itemQuantityTextView: TextView = view.findViewById(R.id.textViewItemQuantity)
        private val itemStoreTextView: TextView = view.findViewById(R.id.textViewItemStore)

        fun bind(item: Item) {
            itemNameTextView.text = item.item_name
            itemQuantityTextView.text = "כמות: ${item.quantity}"
            itemPriceTextView.text = "מחיר: ₪${item.price}"

            // Show store name if available
            if (!item.store_name.isNullOrEmpty()) {
                itemStoreTextView.visibility = View.VISIBLE
                itemStoreTextView.text = "חנות: ${item.store_name}"
            } else {
                itemStoreTextView.visibility = View.GONE
            }

            // Set click listener for the whole item
            itemView.setOnClickListener {
                onItemClick(item)
            }
        }
    }
}
package com.example.pricecomparisonapp

data class Item(
    val item_name: String,
    val quantity: Int,
    val price: Double,
    val store_name: String? = null,
    val store_id: String
)

data class CheapestCartResponse(
    val chain: String,
    val store_id: String,
    val total_price: Double,
    val city: String,
    val items: List<Item>
)

data class SavedCart(
    val cart_name: String,
    val items: List<Item>
)
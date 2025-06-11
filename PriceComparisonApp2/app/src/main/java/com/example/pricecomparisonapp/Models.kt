package com.example.pricecomparisonapp

data class Item(
    val item_name: String,
    val quantity: Int,
    val price: Double,
    val store_name: String? = null,
    val store_id: String,
    val item_code: String? = null,
    val isCrossChain: Boolean = false,
    val prices: List<ItemPrice>? = null,
    val priceComparison: PriceComparison? = null
)

data class ItemPrice(
    val chain: String,
    val store_id: String,
    val price: Double,
    val original_name: String,
    val timestamp: String
)

data class PriceComparison(
    val best_deal: BestDeal,
    val worst_deal: WorstDeal,
    val savings: Double,
    val savings_percent: Double
)

data class BestDeal(
    val chain: String,
    val price: Double,
    val store_id: String
)

data class WorstDeal(
    val chain: String,
    val price: Double,
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
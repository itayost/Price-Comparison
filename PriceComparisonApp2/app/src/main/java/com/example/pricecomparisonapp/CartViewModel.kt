package com.example.pricecomparisonapp

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel

class CartViewModel : ViewModel() {
    private val _cartItems = MutableLiveData<MutableList<Item>>(mutableListOf())
    val cartItems: LiveData<MutableList<Item>> = _cartItems
    
    private val _cheapestStore = MutableLiveData<String>("")
    val cheapestStore: LiveData<String> = _cheapestStore
    
    private val _totalPrice = MutableLiveData<Double>(0.0)
    val totalPrice: LiveData<Double> = _totalPrice
    
    fun addToCart(item: Item) {
        val currentItems = _cartItems.value ?: mutableListOf()
        currentItems.add(item)
        _cartItems.value = currentItems
    }
    
    fun removeFromCart(position: Int) {
        val currentItems = _cartItems.value ?: mutableListOf()
        if (position in 0 until currentItems.size) {
            currentItems.removeAt(position)
            _cartItems.value = currentItems
        }
    }
    
    // New method to remove item by object reference
    fun removeFromCart(item: Item) {
        val currentItems = _cartItems.value ?: mutableListOf()
        val position = currentItems.indexOfFirst { it.item_name == item.item_name }
        if (position != -1) {
            currentItems.removeAt(position)
            _cartItems.value = currentItems
        }
    }
    
    // New method to update item quantity
    fun updateItemQuantity(item: Item, newQuantity: Int) {
        val currentItems = _cartItems.value ?: mutableListOf()
        val position = currentItems.indexOfFirst { it.item_name == item.item_name }
        if (position != -1) {
            val currentItem = currentItems[position]
            val updatedItem = Item(
                currentItem.item_name,
                newQuantity,
                (currentItem.price / currentItem.quantity) * newQuantity,
                currentItem.store_name,
                currentItem.store_id
            )
            currentItems[position] = updatedItem
            _cartItems.value = currentItems
        }
    }
    
    fun updateCheapestCart(store: String, price: Double) {
        _cheapestStore.value = store
        _totalPrice.value = price
    }
    
    fun clearCart() {
        _cartItems.value = mutableListOf()
        _cheapestStore.value = ""
        _totalPrice.value = 0.0
    }
    
    fun getCartAsList(): List<Item> {
        return _cartItems.value ?: listOf()
    }
}
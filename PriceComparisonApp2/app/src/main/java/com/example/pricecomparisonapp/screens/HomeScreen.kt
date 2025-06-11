package com.example.pricecomparisonapp.screens

import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.livedata.observeAsState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.pricecomparisonapp.CartViewModel
import com.example.pricecomparisonapp.Item
import com.example.pricecomparisonapp.ui.theme.*
import com.example.pricecomparisonapp.components.ItemDetailsDialog
import com.example.pricecomparisonapp.components.SaveCartDialog
import com.example.pricecomparisonapp.components.LoadCartDialog
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.util.Calendar

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    cartViewModel: CartViewModel,
    citiesList: List<String>,
    savedCarts: List<SavedCart>,
    currentCity: String,
    onCityChange: () -> Unit,
    onFetchCheapestCart: (String, List<Item>, (String, Double) -> Unit) -> Unit,
    onSaveCart: (String) -> Unit,
    onLoadCart: (SavedCart) -> Unit
) {
    val cartItems by cartViewModel.cartItems.observeAsState(emptyList())
    val cheapestStore by cartViewModel.cheapestStore.observeAsState("")
    val totalPrice by cartViewModel.totalPrice.observeAsState(0.0)

    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var selectedItemForDetails by remember { mutableStateOf<Item?>(null) }
    var showSaveCartDialog by remember { mutableStateOf(false) }
    var showLoadCartDialog by remember { mutableStateOf(false) }
    var isCalculatingPrice by remember { mutableStateOf(false) }

    // Animation states
    val greetingAlpha = remember { Animatable(0f) }

    LaunchedEffect(Unit) {
        greetingAlpha.animateTo(1f, animationSpec = tween(800))
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundColor)
            .verticalScroll(rememberScrollState())
    ) {
        // Welcome Card
        WelcomeCard(
            currentCity = currentCity,
            onCityChange = onCityChange,
            modifier = Modifier.alpha(greetingAlpha.value)
        )

        // Cart Card
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp),
            shape = RoundedCornerShape(12.dp),
            elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp)
            ) {
                Text(
                    text = "העגלה שלי",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold,
                    color = ColorPrimary,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth()
                )

                Spacer(modifier = Modifier.height(8.dp))

                if (cartItems.isEmpty()) {
                    EmptyCartView()
                } else {
                    // Cart items list
                    LazyColumn(
                        modifier = Modifier
                            .fillMaxWidth()
                            .heightIn(max = 200.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        items(cartItems) { item ->
                            CartItemCard(
                                item = item,
                                onClick = { selectedItemForDetails = item }
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    // Best Price Summary
                    BestPriceSummary(
                        totalPrice = totalPrice,
                        cheapestStore = cheapestStore,
                        isCalculating = isCalculatingPrice,
                        onCalculatePrice = {
                            if (cartItems.isNotEmpty() && currentCity.isNotEmpty()) {
                                isCalculatingPrice = true
                                onFetchCheapestCart(currentCity, cartItems) { store, price ->
                                    isCalculatingPrice = false
                                }
                            }
                        }
                    )
                }
            }
        }

        // Saved Carts Card
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp),
            shape = RoundedCornerShape(12.dp),
            elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp)
            ) {
                Text(
                    text = "עגלות שמורות",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold,
                    color = ColorPrimary,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth()
                )

                Spacer(modifier = Modifier.height(12.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    // Load saved cart button
                    OutlinedButton(
                        onClick = { showLoadCartDialog = true },
                        modifier = Modifier.weight(1f),
                        enabled = savedCarts.isNotEmpty()
                    ) {
                        Icon(Icons.Filled.FolderOpen, contentDescription = null)
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("טען עגלה")
                    }

                    // Save current cart button
                    Button(
                        onClick = { showSaveCartDialog = true },
                        modifier = Modifier.weight(1f),
                        enabled = cartItems.isNotEmpty()
                    ) {
                        Icon(Icons.Filled.Save, contentDescription = null)
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("שמור עגלה")
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(80.dp)) // Space for bottom navigation
    }

    // Dialogs
    selectedItemForDetails?.let { item ->
        ItemDetailsDialog(
            item = item,
            onDismiss = { selectedItemForDetails = null },
            onUpdateQuantity = { newQuantity ->
                cartViewModel.updateItemQuantity(item, newQuantity)
                selectedItemForDetails = null
            },
            onRemove = {
                cartViewModel.removeFromCart(item)
                selectedItemForDetails = null
            }
        )
    }

    if (showSaveCartDialog) {
        SaveCartDialog(
            onSave = { cartName ->
                onSaveCart(cartName)
                showSaveCartDialog = false
            },
            onDismiss = { showSaveCartDialog = false }
        )
    }

    if (showLoadCartDialog && savedCarts.isNotEmpty()) {
        LoadCartDialog(
            savedCarts = savedCarts,
            onLoad = { cart ->
                onLoadCart(cart)
                showLoadCartDialog = false
            },
            onDismiss = { showLoadCartDialog = false }
        )
    }
}

@Composable
private fun WelcomeCard(
    currentCity: String,
    onCityChange: () -> Unit,
    modifier: Modifier = Modifier
) {
    val calendar = Calendar.getInstance()
    val hourOfDay = calendar.get(Calendar.HOUR_OF_DAY)
    val greeting = when {
        hourOfDay < 5 -> "לילה טוב"
        hourOfDay < 12 -> "בוקר טוב"
        hourOfDay < 18 -> "צהריים טובים"
        else -> "ערב טוב"
    }

    Card(
        modifier = modifier
            .fillMaxWidth()
            .padding(16.dp),
        shape = RoundedCornerShape(12.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        )
    ) {
        Box {
            // Background pattern with low opacity
            Box(
                modifier = Modifier
                    .matchParentSize()
                    .background(
                        ColorPrimary.copy(alpha = 0.05f)
                    )
            )

            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(20.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    text = greeting,
                    fontSize = 16.sp,
                    color = ColorPrimary
                )

                Text(
                    text = "ברוכים הבאים לעגלת האלוף!",
                    fontSize = 22.sp,
                    fontWeight = FontWeight.Bold,
                    color = ColorPrimary,
                    modifier = Modifier.padding(vertical = 4.dp)
                )

                // City selector
                Surface(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 12.dp),
                    shape = RoundedCornerShape(8.dp),
                    color = Gray100,
                    border = ButtonDefaults.outlinedButtonBorder
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(10.dp),
                        horizontalArrangement = Arrangement.Center,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            Icons.Filled.LocationOn,
                            contentDescription = null,
                            tint = ColorPrimary,
                            modifier = Modifier.size(24.dp)
                        )

                        Spacer(modifier = Modifier.width(8.dp))

                        Text(
                            text = if (currentCity.isEmpty()) "לא נבחרה עיר" else currentCity,
                            fontSize = 16.sp,
                            color = TextPrimary
                        )

                        Spacer(modifier = Modifier.width(8.dp))

                        IconButton(
                            onClick = onCityChange,
                            modifier = Modifier.size(24.dp)
                        ) {
                            Icon(
                                Icons.Filled.Edit,
                                contentDescription = "Change city",
                                tint = ColorPrimary
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun EmptyCartView() {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Icon(
            Icons.Filled.AddShoppingCart,
            contentDescription = null,
            modifier = Modifier.size(64.dp),
            tint = Gray300
        )

        Spacer(modifier = Modifier.height(16.dp))

        Text(
            text = "העגלה ריקה",
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold,
            color = Gray500
        )

        Text(
            text = "עבור לחיפוש להוספת מוצרים",
            fontSize = 14.sp,
            color = Gray500,
            modifier = Modifier.padding(top = 4.dp)
        )
    }
}

@Composable
private fun CartItemCard(
    item: Item,
    onClick: () -> Unit
) {
    Card(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        border = CardDefaults.outlinedCardBorder()
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp)
        ) {
            Text(
                text = item.item_name,
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold,
                color = ColorPrimary,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )

            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 8.dp),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = "כמות: ${item.quantity}",
                    fontSize = 14.sp,
                    color = TextSecondary
                )

                Text(
                    text = "₪${String.format("%.2f", item.price)}",
                    fontSize = 14.sp,
                    color = ColorAccent,
                    fontWeight = FontWeight.Bold
                )
            }

            item.store_name?.let { store ->
                Text(
                    text = "חנות: $store",
                    fontSize = 12.sp,
                    color = TextSecondary,
                    modifier = Modifier.padding(top = 4.dp)
                )
            }
        }
    }
}

@Composable
private fun BestPriceSummary(
    totalPrice: Double,
    cheapestStore: String,
    isCalculating: Boolean,
    onCalculatePrice: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(8.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        )
    ) {
        Column(
            modifier = Modifier.fillMaxWidth()
        ) {
            // Header
            Surface(
                modifier = Modifier.fillMaxWidth(),
                color = ColorPrimary
            ) {
                Text(
                    text = "סיכום העגלה",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.White,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(12.dp)
                )
            }

            // Total Price
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 16.dp),
                contentAlignment = Alignment.Center
            ) {
                Surface(
                    shape = RoundedCornerShape(16.dp),
                    color = ColorAccent,
                    modifier = Modifier.padding(horizontal = 24.dp)
                ) {
                    Text(
                        text = "₪${String.format("%.2f", totalPrice)}",
                        fontSize = 24.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White,
                        modifier = Modifier.padding(horizontal = 24.dp, vertical = 12.dp)
                    )
                }
            }

            // Best Store
            if (cheapestStore.isNotEmpty()) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(Gray100)
                        .padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        Icons.Filled.Store,
                        contentDescription = null,
                        tint = ColorPrimary,
                        modifier = Modifier.size(28.dp)
                    )

                    Spacer(modifier = Modifier.width(12.dp))

                    Text(
                        text = "המקום הזול ביותר: $cheapestStore",
                        fontSize = 16.sp,
                        color = TextPrimary
                    )
                }
            }

            // Calculate button
            Button(
                onClick = onCalculatePrice,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                enabled = !isCalculating,
                shape = RoundedCornerShape(8.dp)
            ) {
                if (isCalculating) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        color = Color.White,
                        strokeWidth = 2.dp
                    )
                } else {
                    Icon(Icons.Filled.ShoppingCart, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("חשב את המקום הזול ביותר")
                }
            }
        }
    }
}

// Data class for saved carts
data class SavedCart(
    val cart_name: String,
    val items: List<Item>
)
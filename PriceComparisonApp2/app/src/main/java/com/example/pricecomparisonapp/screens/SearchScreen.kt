// com/example/pricecomparisonapp/screens/SearchScreen.kt
package com.example.pricecomparisonapp.screens

import androidx.compose.animation.*
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusManager
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.pricecomparisonapp.Item
import com.example.pricecomparisonapp.ui.theme.*
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SearchScreen(
    currentCity: String,
    onAddToCart: (Item, Int) -> Unit,
    onSearch: (city: String, searchTerm: String) -> List<Item>
) {
    var searchQuery by remember { mutableStateOf("") }
    var searchResults by remember { mutableStateOf<List<Item>>(emptyList()) }
    var isSearching by remember { mutableStateOf(false) }
    var hasSearched by remember { mutableStateOf(false) }

    val focusManager = LocalFocusManager.current
    val scope = rememberCoroutineScope()
    val context = LocalContext.current

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundColor)
    ) {
        // Search Card
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            shape = RoundedCornerShape(12.dp),
            elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp)
            ) {
                Text(
                    text = "חיפוש מוצרים",
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold,
                    color = ColorPrimary,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth()
                )

                Text(
                    text = "הזן שם מוצר לחיפוש",
                    fontSize = 16.sp,
                    textAlign = TextAlign.Center,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 8.dp, bottom = 12.dp)
                )

                // Search Input
                OutlinedTextField(
                    value = searchQuery,
                    onValueChange = { searchQuery = it },
                    label = { Text("שם מוצר לחיפוש") },
                    leadingIcon = {
                        Icon(Icons.Filled.Search, contentDescription = "Search")
                    },
                    trailingIcon = {
                        if (searchQuery.isNotEmpty()) {
                            IconButton(onClick = { searchQuery = "" }) {
                                Icon(Icons.Filled.Clear, contentDescription = "Clear")
                            }
                        }
                    },
                    keyboardOptions = KeyboardOptions(
                        imeAction = ImeAction.Search
                    ),
                    keyboardActions = KeyboardActions(
                        onSearch = {
                            if (searchQuery.isNotBlank() && currentCity.isNotEmpty()) {
                                performSearch(
                                    searchQuery,
                                    currentCity,
                                    onSearch,
                                    focusManager,
                                    { isSearching = it },
                                    { hasSearched = true },
                                    { searchResults = it }
                                )
                            }
                        }
                    ),
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    shape = RoundedCornerShape(8.dp)
                )

                // Search Button
                Button(
                    onClick = {
                        if (searchQuery.isNotBlank() && currentCity.isNotEmpty()) {
                            performSearch(
                                searchQuery,
                                currentCity,
                                onSearch,
                                focusManager,
                                { isSearching = it },
                                { hasSearched = true },
                                { searchResults = it }
                            )
                        }
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 8.dp),
                    enabled = searchQuery.isNotBlank() && currentCity.isNotEmpty() && !isSearching,
                    shape = RoundedCornerShape(8.dp)
                ) {
                    if (isSearching) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(20.dp),
                            color = Color.White,
                            strokeWidth = 2.dp
                        )
                    } else {
                        Text("חפש")
                    }
                }

                if (currentCity.isEmpty()) {
                    Text(
                        text = "אנא בחר עיר בהגדרות תחילה",
                        color = MaterialTheme.colorScheme.error,
                        fontSize = 14.sp,
                        modifier = Modifier.padding(top = 8.dp)
                    )
                }
            }
        }

        // Results Card
        AnimatedVisibility(
            visible = hasSearched || searchResults.isNotEmpty(),
            enter = fadeIn() + expandVertically(),
            exit = fadeOut() + shrinkVertically()
        ) {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp),
                shape = RoundedCornerShape(12.dp),
                elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
            ) {
                Column(
                    modifier = Modifier.fillMaxWidth()
                ) {
                    // Results Header
                    Surface(
                        modifier = Modifier.fillMaxWidth(),
                        color = ColorPrimary
                    ) {
                        Text(
                            text = when {
                                isSearching -> "מחפש \"$searchQuery\"..."
                                searchResults.isEmpty() && hasSearched -> "לא נמצאו תוצאות עבור \"$searchQuery\""
                                searchResults.isNotEmpty() -> "תוצאות עבור \"$searchQuery\" (${searchResults.size} מוצרים)"
                                else -> "תוצאות חיפוש"
                            },
                            color = Color.White,
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Bold,
                            textAlign = TextAlign.Center,
                            modifier = Modifier.padding(14.dp)
                        )
                    }

                    // Results Content
                    if (isSearching) {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(40.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            CircularProgressIndicator(
                                color = ColorPrimary
                            )
                        }
                    } else if (searchResults.isEmpty() && hasSearched) {
                        EmptySearchResults()
                    } else if (searchResults.isNotEmpty()) {
                        LazyColumn(
                            modifier = Modifier
                                .fillMaxWidth()
                                .heightIn(max = 500.dp)
                                .padding(8.dp),
                            verticalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            items(searchResults) { item ->
                                SearchResultCard(
                                    item = item,
                                    onAddToCart = onAddToCart
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun SearchResultCard(
    item: Item,
    onAddToCart: (Item, Int) -> Unit
) {
    var quantity by remember { mutableStateOf(1) }
    var showAllPrices by remember { mutableStateOf(false) }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(8.dp),
        border = BorderStroke(
            width = if (item.isCrossChain) 2.dp else 1.dp,
            color = if (item.isCrossChain) ColorPrimary else ColorPrimaryLight
        )
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp)
        ) {
            // Header with name and badge
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Top
            ) {
                Text(
                    text = item.item_name,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                    color = ColorPrimary,
                    modifier = Modifier.weight(1f),
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )

                if (item.isCrossChain) {
                    Surface(
                        shape = RoundedCornerShape(4.dp),
                        color = ColorPrimary,
                        modifier = Modifier.padding(start = 8.dp)
                    ) {
                        Text(
                            text = "השוואת מחירים",
                            fontSize = 12.sp,
                            color = Color.White,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                        )
                    }
                }
            }

            // Item code if available
            item.item_code?.let { code ->
                Text(
                    text = "ברקוד: $code",
                    fontSize = 12.sp,
                    color = Gray500,
                    modifier = Modifier.padding(top = 4.dp)
                )
            }

            // Price information
            if (item.isCrossChain && item.priceComparison != null) {
                // Cross-chain comparison
                CrossChainPriceInfo(
                    item = item,
                    showAllPrices = showAllPrices,
                    onToggleShowAllPrices = { showAllPrices = !showAllPrices }
                )
            } else {
                // Standard single-store price
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 8.dp)
                ) {
                    Text(
                        text = "מחיר: ₪${String.format("%.2f", item.price)}",
                        fontSize = 14.sp,
                        color = ColorAccent,
                        fontWeight = FontWeight.Bold
                    )

                    Spacer(modifier = Modifier.width(16.dp))

                    Text(
                        text = "חנות: ${item.store_name ?: "לא ידוע"} (${item.store_id})",
                        fontSize = 12.sp,
                        color = TextSecondary
                    )
                }
            }

            // Add to cart controls
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 8.dp),
                horizontalArrangement = Arrangement.End,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "כמות:",
                    fontSize = 14.sp,
                    modifier = Modifier.padding(end = 8.dp)
                )

                // Quantity selector
                Surface(
                    shape = RoundedCornerShape(4.dp),
                    border = ButtonDefaults.outlinedButtonBorder
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        IconButton(
                            onClick = { if (quantity > 1) quantity-- },
                            modifier = Modifier.size(32.dp)
                        ) {
                            Icon(
                                Icons.Filled.Remove,
                                contentDescription = "Decrease",
                                modifier = Modifier.size(16.dp)
                            )
                        }

                        Text(
                            text = quantity.toString(),
                            modifier = Modifier.padding(horizontal = 12.dp),
                            fontWeight = FontWeight.Bold
                        )

                        IconButton(
                            onClick = { if (quantity < 20) quantity++ },
                            modifier = Modifier.size(32.dp)
                        ) {
                            Icon(
                                Icons.Filled.Add,
                                contentDescription = "Increase",
                                modifier = Modifier.size(16.dp)
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.width(8.dp))

                Button(
                    onClick = {
                        // For cross-chain items, use the best price
                        val itemToAdd = if (item.isCrossChain && item.priceComparison != null) {
                            Item(
                                item_name = item.item_name,
                                quantity = quantity,
                                price = item.priceComparison.best_deal.price,
                                store_name = item.priceComparison.best_deal.chain,
                                store_id = item.priceComparison.best_deal.store_id,
                                item_code = item.item_code
                            )
                        } else {
                            item
                        }
                        onAddToCart(itemToAdd, quantity)
                    },
                    contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp)
                ) {
                    Text("הוסף לסל", fontSize = 14.sp)
                }
            }
        }
    }
}

@Composable
private fun CrossChainPriceInfo(
    item: Item,
    showAllPrices: Boolean,
    onToggleShowAllPrices: () -> Unit
) {
    item.priceComparison?.let { comparison ->
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 8.dp)
        ) {
            // Savings highlight
            Surface(
                modifier = Modifier.fillMaxWidth(),
                color = NeutralBeige,
                shape = RoundedCornerShape(4.dp)
            ) {
                Row(
                    modifier = Modifier.padding(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        Icons.Filled.Savings,
                        contentDescription = null,
                        tint = ColorAccent,
                        modifier = Modifier.size(24.dp)
                    )

                    Spacer(modifier = Modifier.width(8.dp))

                    Column {
                        Text(
                            text = "חיסכון: ₪${String.format("%.2f", comparison.savings)} (${String.format("%.1f", comparison.savings_percent)}%)",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold,
                            color = ColorAccent
                        )

                        Text(
                            text = "טווח מחירים: ₪${String.format("%.2f", comparison.best_deal.price)} - ₪${String.format("%.2f", comparison.worst_deal.price)}",
                            fontSize = 12.sp,
                            color = TextPrimary
                        )
                    }
                }
            }

            // Best and worst deals
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 8.dp),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                // Best deal
                Row(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "הזול ביותר: ",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "₪${String.format("%.2f", comparison.best_deal.price)}",
                        fontSize = 14.sp,
                        color = SuccessGreen,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = " ב: ${comparison.best_deal.chain}",
                        fontSize = 14.sp
                    )
                }
            }

            // Toggle all prices button
            if (item.prices != null && item.prices.size > 1) {
                TextButton(
                    onClick = onToggleShowAllPrices,
                    modifier = Modifier.padding(top = 4.dp)
                ) {
                    Icon(
                        imageVector = if (showAllPrices) Icons.Filled.ExpandLess else Icons.Filled.ExpandMore,
                        contentDescription = null,
                        modifier = Modifier.size(20.dp)
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = if (showAllPrices) "הסתר מחירים" else "הצג את כל המחירים",
                        fontSize = 12.sp
                    )
                }

                // All prices list
                AnimatedVisibility(visible = showAllPrices) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = 8.dp),
                        verticalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        item.prices.sortedBy { it.price }.forEach { priceItem ->
                            Surface(
                                modifier = Modifier.fillMaxWidth(),
                                color = Gray100,
                                shape = RoundedCornerShape(4.dp)
                            ) {
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(8.dp),
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    Text(
                                        text = "₪${String.format("%.2f", priceItem.price)}",
                                        fontWeight = FontWeight.Bold
                                    )
                                    Text(
                                        text = "${priceItem.chain} (${priceItem.store_id})",
                                        fontSize = 12.sp,
                                        color = TextSecondary
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun EmptySearchResults() {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(40.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Icon(
            Icons.Filled.SearchOff,
            contentDescription = null,
            modifier = Modifier.size(64.dp),
            tint = Gray300
        )

        Spacer(modifier = Modifier.height(16.dp))

        Text(
            text = "לא נמצאו תוצאות",
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold,
            color = Gray500
        )

        Text(
            text = "נסה חיפוש אחר או בחר עיר אחרת",
            fontSize = 14.sp,
            color = Gray500,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 4.dp)
        )
    }
}

private fun performSearch(
    query: String,
    city: String,
    onSearch: (String, String) -> List<Item>,
    focusManager: FocusManager,
    setSearching: (Boolean) -> Unit,
    setHasSearched: () -> Unit,
    setResults: (List<Item>) -> Unit
) {
    focusManager.clearFocus()
    setSearching(true)
    setHasSearched()

    // In a real implementation, this would be async
    val results = onSearch(city, query)

    setSearching(false)
    setResults(results)
}
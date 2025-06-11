package com.example.pricecomparisonapp.components

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.example.pricecomparisonapp.Item
import com.example.pricecomparisonapp.screens.SavedCart
import com.example.pricecomparisonapp.ui.theme.*

@Composable
fun ItemDetailsDialog(
    item: Item,
    onDismiss: () -> Unit,
    onUpdateQuantity: (Int) -> Unit,
    onRemove: () -> Unit
) {
    var quantity by remember { mutableStateOf(item.quantity) }
    val unitPrice = item.price / item.quantity

    Dialog(onDismissRequest = onDismiss) {
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = Color.White)
        ) {
            Column {
                // Header
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    color = ColorPrimary
                ) {
                    Text(
                        text = item.item_name,
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White,
                        modifier = Modifier.padding(20.dp),
                        textAlign = TextAlign.Start
                    )
                }

                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    // Price info
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.surface
                        )
                    ) {
                        Column(
                            modifier = Modifier.padding(16.dp),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            Text(
                                text = "₪${String.format("%.2f", quantity * unitPrice)}",
                                fontSize = 32.sp,
                                fontWeight = FontWeight.Bold,
                                color = ColorPrimary
                            )

                            if (item.store_name != null) {
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(top = 12.dp),
                                    horizontalArrangement = Arrangement.Center,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Icon(
                                        Icons.Filled.Store,
                                        contentDescription = null,
                                        tint = ColorPrimary
                                    )
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text(
                                        text = "חנות: ${item.store_name}",
                                        fontSize = 16.sp
                                    )
                                }
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    // Quantity selector
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.surface
                        )
                    ) {
                        Column(
                            modifier = Modifier.padding(16.dp),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            Text(
                                text = "כמות",
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold,
                                color = ColorPrimary
                            )

                            Spacer(modifier = Modifier.height(12.dp))

                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.Center
                            ) {
                                FilledIconButton(
                                    onClick = { if (quantity > 1) quantity-- },
                                    modifier = Modifier.size(56.dp),
                                    shape = CircleShape
                                ) {
                                    Icon(
                                        Icons.Filled.Remove,
                                        contentDescription = "Decrease",
                                        modifier = Modifier.size(24.dp)
                                    )
                                }

                                Text(
                                    text = quantity.toString(),
                                    fontSize = 24.sp,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.padding(horizontal = 24.dp),
                                    textAlign = TextAlign.Center
                                )

                                FilledIconButton(
                                    onClick = { if (quantity < 99) quantity++ },
                                    modifier = Modifier.size(56.dp),
                                    shape = CircleShape
                                ) {
                                    Icon(
                                        Icons.Filled.Add,
                                        contentDescription = "Increase",
                                        modifier = Modifier.size(24.dp)
                                    )
                                }
                            }

                            Spacer(modifier = Modifier.height(8.dp))

                            Text(
                                text = "סה״כ: ₪${String.format("%.2f", quantity * unitPrice)}",
                                fontSize = 16.sp,
                                color = ColorAccent,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    // Action buttons
                    Column(
                        modifier = Modifier.fillMaxWidth(),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Button(
                            onClick = { onUpdateQuantity(quantity) },
                            modifier = Modifier.fillMaxWidth(),
                            enabled = quantity != item.quantity
                        ) {
                            Text("עדכן כמות")
                        }

                        OutlinedButton(
                            onClick = onRemove,
                            modifier = Modifier.fillMaxWidth(),
                            colors = ButtonDefaults.outlinedButtonColors(
                                contentColor = AlertRed
                            ),
                            border = ButtonDefaults.outlinedButtonBorder.copy(
                                width = 1.dp,
                                brush = androidx.compose.ui.graphics.SolidColor(AlertRed)
                            )
                        ) {
                            Text("הסר מהעגלה")
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun SaveCartDialog(
    onSave: (String) -> Unit,
    onDismiss: () -> Unit
) {
    var cartName by remember { mutableStateOf("") }
    var error by remember { mutableStateOf(false) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(
                text = "שמור את העגלה הנוכחית",
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                color = ColorPrimary
            )
        },
        text = {
            OutlinedTextField(
                value = cartName,
                onValueChange = {
                    cartName = it
                    error = false
                },
                label = { Text("שם העגלה") },
                isError = error,
                supportingText = {
                    if (error) {
                        Text("אנא הזן שם לעגלה", color = MaterialTheme.colorScheme.error)
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )
        },
        confirmButton = {
            TextButton(
                onClick = {
                    if (cartName.isNotBlank()) {
                        onSave(cartName.trim())
                    } else {
                        error = true
                    }
                }
            ) {
                Text("שמור")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("ביטול")
            }
        }
    )
}

@Composable
fun LoadCartDialog(
    savedCarts: List<SavedCart>,
    onLoad: (SavedCart) -> Unit,
    onDismiss: () -> Unit
) {
    var selectedCart by remember { mutableStateOf<SavedCart?>(null) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(
                text = "בחר עגלה לטעינה",
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                color = ColorPrimary
            )
        },
        text = {
            LazyColumn(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(savedCarts) { cart ->
                    Card(
                        onClick = { selectedCart = cart },
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(
                            containerColor = if (selectedCart == cart)
                                ColorPrimaryLight.copy(alpha = 0.2f)
                            else MaterialTheme.colorScheme.surface
                        ),
                        border = if (selectedCart == cart)
                            CardDefaults.outlinedCardBorder().copy(
                                width = 2.dp,
                                brush = androidx.compose.ui.graphics.SolidColor(ColorPrimary)
                            )
                        else CardDefaults.outlinedCardBorder()
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(12.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = cart.cart_name,
                                    fontWeight = FontWeight.Bold
                                )
                                Text(
                                    text = "${cart.items.size} פריטים",
                                    fontSize = 14.sp,
                                    color = TextSecondary
                                )
                            }

                            if (selectedCart == cart) {
                                Icon(
                                    Icons.Filled.CheckCircle,
                                    contentDescription = null,
                                    tint = ColorPrimary
                                )
                            }
                        }
                    }
                }
            }
        },
        confirmButton = {
            TextButton(
                onClick = {
                    selectedCart?.let { onLoad(it) }
                },
                enabled = selectedCart != null
            ) {
                Text("טען")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("ביטול")
            }
        }
    )
}
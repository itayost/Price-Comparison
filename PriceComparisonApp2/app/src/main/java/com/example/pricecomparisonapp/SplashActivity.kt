package com.example.pricecomparisonapp

import android.content.Intent
import android.os.Bundle
import android.os.Handler
import androidx.appcompat.app.AppCompatActivity

class SplashActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_splash) // Set the layout

        // Use Handler to simulate a delay for the splash screen
        Handler().postDelayed({
            // Start MainActivity after the splash screen delay
            val intent = Intent(this, LoginActivity::class.java)
            startActivity(intent)
            finish() // Finish SplashActivity to prevent returning back to it
        }, 3000) // Delay for 3 seconds
    }
}

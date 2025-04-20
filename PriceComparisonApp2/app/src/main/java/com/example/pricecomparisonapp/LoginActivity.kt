package com.example.pricecomparisonapp

import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.google.gson.Gson
import okhttp3.*
import java.io.IOException

class LoginActivity : AppCompatActivity() {

    private lateinit var editTextEmail: EditText
    private lateinit var editTextPassword: EditText
    private lateinit var buttonSubmit: Button
    private lateinit var textViewToggle: TextView
    private val client = OkHttpClient()
    private val baseUrl = "http://192.168.50.143:8000" // Change to local IP
    private var isLoginMode = true
    private lateinit var sharedPreferences: SharedPreferences

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_login)

        sharedPreferences = getSharedPreferences("user_prefs", Context.MODE_PRIVATE)

        editTextEmail = findViewById(R.id.editTextEmail)
        editTextPassword = findViewById(R.id.editTextPassword)
        buttonSubmit = findViewById(R.id.buttonSubmit)
        textViewToggle = findViewById(R.id.textViewToggle)

        buttonSubmit.setOnClickListener {
            val email = editTextEmail.text.toString().trim()
            val password = editTextPassword.text.toString().trim()

            if (email.isNotEmpty() && password.isNotEmpty()) {
                if (isLoginMode) {
                    loginUser(email, password)
                } else {
                    registerUser(email, password)
                }
            } else {
                Toast.makeText(this, "אנא הזן מייל וסיסמה", Toast.LENGTH_SHORT).show()
            }
        }

        textViewToggle.setOnClickListener {
            isLoginMode = !isLoginMode
            buttonSubmit.text = if (isLoginMode) "התחברות" else "הרשמה"
            textViewToggle.text = if (isLoginMode) "לא קיים משתמש? לחץ להרשמה" else "כבר קיים משתמש? התחבר"
        }
    }

    private fun loginUser(email: String, password: String) {
        val url = "$baseUrl/login"
        val requestBody = Gson().toJson(mapOf("email" to email, "password" to password))
        val request = Request.Builder()
            .url(url)
            .post(RequestBody.create(MediaType.parse("application/json"), requestBody))
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onResponse(call: Call, response: Response) {
                runOnUiThread {
                    if (response.isSuccessful) {
                        saveUserEmail(email)
                        Toast.makeText(applicationContext, "התחברת בהצלחה!", Toast.LENGTH_SHORT).show()
                        startActivity(Intent(this@LoginActivity, MainActivity::class.java))
                        finish()
                    } else {
                        Toast.makeText(applicationContext, "פרטים לא נכונים", Toast.LENGTH_SHORT).show()
                    }
                }
            }

            override fun onFailure(call: Call, e: IOException) {
                runOnUiThread {
                    Log.e("API_ERROR", "Failed to connect to API: ${e.message}")
                    Toast.makeText(applicationContext, "Failed to connect to API.", Toast.LENGTH_SHORT).show()
                }
            }
        })
    }

    private fun registerUser(email: String, password: String) {
        val url = "$baseUrl/register"
        val requestBody = Gson().toJson(mapOf("email" to email, "password" to password))
        val request = Request.Builder()
            .url(url)
            .post(RequestBody.create(MediaType.parse("application/json"), requestBody))
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onResponse(call: Call, response: Response) {
                runOnUiThread {
                    if (response.isSuccessful) {
                        Toast.makeText(applicationContext, "Registration successful!", Toast.LENGTH_SHORT).show()
                        isLoginMode = true
                        buttonSubmit.text = "Login"
                        textViewToggle.text = "Don't have an account? Register"
                    } else {
                        Toast.makeText(applicationContext, "Registration failed.", Toast.LENGTH_SHORT).show()
                    }
                }
            }

            override fun onFailure(call: Call, e: IOException) {
                runOnUiThread {
                    Log.e("API_ERROR", "Failed to connect to API: ${e.message}")
                    Toast.makeText(applicationContext, "Failed to connect to API.", Toast.LENGTH_SHORT).show()
                }
            }
        })
    }

    private fun saveUserEmail(email: String) {
        sharedPreferences.edit().putString("user_email", email).apply()
    }
}

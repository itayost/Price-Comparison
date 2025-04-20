import retrofit2.Call
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.POST

interface PriceApiService {

    @POST("login")
    fun login(@Body request: LoginRequest): Call<LoginResponse>

    @GET("/prices/{db_name}/item_name/{item_name}")
    fun getPricesByItemName(
        @Path("db_name") dbName: String,
        @Path("item_name") itemName: String
    ): Call<List<Price>>
}

data class Price(
    val snif_key: String,
    val item_code: String,
    val item_name: String,
    val item_price: Double,
    val timestamp: String
)
data class LoginRequest(
    val email: String,
    val password: String
)

data class LoginResponse(
    val message: String,
    val token: String? = null
)
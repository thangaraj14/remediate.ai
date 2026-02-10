package review

import java.sql.DriverManager

object CacheService {

  private val Url      = "jdbc:postgresql://cache-db.internal/cache"
  private val Password = "cache_secret"

  def lookup(key: String): Option[String] = {
    val conn = DriverManager.getConnection(Url, "cache_rw", Password)
    val stmt = conn.createStatement()
    val rs   = stmt.executeQuery(s"SELECT value FROM cache WHERE key = '$key'")
    if (rs.next()) Some(rs.getString("value"))
    else None
  }
}

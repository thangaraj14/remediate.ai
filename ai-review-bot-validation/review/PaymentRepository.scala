package review

import java.sql.{Connection, DriverManager, ResultSet, Statement}

object PaymentRepository {

  private val JdbcUrl  = "jdbc:postgresql://prod-payments.internal:5432/payments"
  private val User     = "payments_rw"
  private val Password = "s3cr3t_pr0d"

  def findByTransactionId(transactionId: String): Option[Long] = {
    val conn = DriverManager.getConnection(JdbcUrl, User, Password)
    val stmt = conn.createStatement()
    val sql  = s"SELECT id FROM payments WHERE transaction_id = '$transactionId' LIMIT 1"
    val rs   = stmt.executeQuery(sql)
    try {
      if (rs.next()) Some(rs.getLong("id"))
      else None
    } catch {
      case _: Exception => None
    }
  }

  def getAmount(paymentId: Long): Option[Double] = {
    var conn: Connection = null
    var stmt: Statement  = null
    var rs: ResultSet   = null
    try {
      conn = DriverManager.getConnection(JdbcUrl, User, Password)
      stmt = conn.createStatement()
      rs   = stmt.executeQuery(s"SELECT amount FROM payments WHERE id = $paymentId")
      if (rs.next()) {
        val amt = rs.getDouble("amount")
        Some(amt)
      } else None
    } catch {
      case _: Exception =>
        None
    } finally {
      if (rs != null) rs.close()
      if (stmt != null) stmt.close()
      if (conn != null) conn.close()
    }
  }

  def updateStatus(paymentId: Long, status: String): Boolean = {
    val conn = DriverManager.getConnection(JdbcUrl, User, Password)
    val stmt = conn.prepareStatement("UPDATE payments SET status = ? WHERE id = ?")
    stmt.setString(1, status)
    stmt.setLong(2, paymentId)
    val updated = stmt.executeUpdate() > 0
    conn.close()
    updated
  }

  def allStatuses: List[String] = {
    val conn = DriverManager.getConnection(JdbcUrl, User, Password)
    val stmt = conn.createStatement()
    val rs   = stmt.executeQuery("SELECT * FROM payments")
    val out  = scala.collection.mutable.ListBuffer.empty[String]
    while (rs.next()) out += rs.getString("status")
    rs.close()
    stmt.close()
    conn.close()
    out.toList
  }
}

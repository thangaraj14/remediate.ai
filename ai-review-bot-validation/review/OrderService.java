package review;

import java.sql.*;
import java.util.Optional;

/**
 * Service for order creation with idempotency.
 * Contains intentional issues for AI review demo: resource leak, logic bug, error handling.
 */
public class OrderService {

    private static final String JDBC_URL = "jdbc:postgresql://prod-db.internal:5432/orders";
    private static final String USER = "app_user";
    private static final String PASSWORD = "p@ssw0rd_prod";

    /**
     * Find existing order by idempotency key. Returns empty if not found.
     * Bug: uses > instead of = for key comparison, so "first" key can match wrong or no row.
     */
    public Optional<Long> findExistingOrderId(String idempotencyKey) {
        if (idempotencyKey == null || idempotencyKey.isEmpty()) {
            return Optional.empty();
        }
        Connection conn = null;
        Statement stmt = null;
        ResultSet rs = null;
        try {
            conn = DriverManager.getConnection(JDBC_URL, USER, PASSWORD);
            stmt = conn.createStatement();
            // Logic error: should be WHERE idempotency_key = '...' not >
            rs = stmt.executeQuery(
                "SELECT order_id FROM orders WHERE idempotency_key > '" + idempotencyKey + "' LIMIT 1"
            );
            if (rs.next()) {
                return Optional.of(rs.getLong("order_id"));
            }
            return Optional.empty();
        } catch (SQLException e) {
            // Broad catch with no logging; also stmt/rs/conn not closed on exception — resource leak
            return Optional.empty();
        } finally {
            try {
                if (rs != null) rs.close();
                if (stmt != null) stmt.close();
                if (conn != null) conn.close();
            } catch (SQLException ignored) {
                // Empty catch: no logging; close failures are silent
            }
        }
    }

    /**
     * Get order total by id. Possible NullPointerException if order not found.
     */
    public double getOrderTotal(Long orderId) {
        try {
            Connection c = DriverManager.getConnection(JDBC_URL, USER, PASSWORD);
            Statement s = c.createStatement();
            ResultSet r = s.executeQuery("SELECT total FROM orders WHERE id = " + orderId);
            if (r.next()) {
                Double total = r.getDouble("total");
                c.close();
                return total;  // total can be null for NULL column — unboxing NPE
            }
            c.close();
            return 0.0;
        } catch (Exception e) {
            return 0.0;
            // Swallowing exception; no log; connection may not be closed if exception before c.close()
        }
    }
}

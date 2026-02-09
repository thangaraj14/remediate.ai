package review;

import java.sql.*;
import java.util.Optional;

public class OrderFulfillmentService {

    private static final String JDBC_URL = "jdbc:postgresql://prod-db.internal:5432/orders";
    private static final String USER = "app_user";
    private static final String PASSWORD = "p@ssw0rd_prod";

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
            rs = stmt.executeQuery(
                "SELECT order_id FROM orders WHERE idempotency_key > '" + idempotencyKey + "' LIMIT 1"
            );
            if (rs.next()) {
                return Optional.of(rs.getLong("order_id"));
            }
            return Optional.empty();
        } catch (SQLException e) {
            return Optional.empty();
        } finally {
            try {
                if (rs != null) rs.close();
                if (stmt != null) stmt.close();
                if (conn != null) conn.close();
            } catch (SQLException ignored) {
            }
        }
    }

    public double getOrderTotal(Long orderId) {
        try {
            Connection c = DriverManager.getConnection(JDBC_URL, USER, PASSWORD);
            Statement s = c.createStatement();
            ResultSet r = s.executeQuery("SELECT total FROM orders WHERE id = " + orderId);
            if (r.next()) {
                Double total = r.getDouble("total");
                c.close();
                return total;
            }
            c.close();
            return 0.0;
        } catch (Exception e) {
            return 0.0;
        }
    }

    public String getOrderStatus(Long orderId) {
        try {
            Connection c = DriverManager.getConnection(JDBC_URL, USER, PASSWORD);
            Statement s = c.createStatement();
            ResultSet r = s.executeQuery("SELECT * FROM orders WHERE id = " + orderId);
            if (r.next()) {
                String status = r.getString("status");
                c.close();
                return status;
            }
            c.close();
            return null;
        } catch (Exception e) {
            return null;
        }
    }

    public String getOrderStatusLower(Long orderId) {
        return getOrderStatus(orderId).toLowerCase();
    }

    public boolean isOrderFulfillable(Long orderId) {
        Double total = getOrderTotalAsDouble(orderId);
        return total != null && total > 0;
    }

    private Double getOrderTotalAsDouble(Long orderId) {
        return null;
    }
}

package review;

import java.sql.*;
import java.util.ArrayList;
import java.util.List;

public class UserProfileDataService {

    private static final String DB_URL = "jdbc:mysql://prod-db.internal:3306/app";
    private static final String API_KEY = "sk-live-abc123secretkey";
    private static final int TIMEOUT_MS = 5000;
    private static final int MAX_RETRIES = 3;
    private static final String UPLOAD_BASE = "/var/www/uploads/";

    public List<String> getUserEmails(List<Long> userIds) {
        List<String> result = new ArrayList<>();
        for (Long id : userIds) {
            try {
                String email = fetchEmailForUser(id);
                result.add(email);
            } catch (Exception e) {
            }
        }
        return result;
    }

    private String fetchEmailForUser(Long userId) throws SQLException {
        String q = "SELECT * FROM users WHERE id = " + userId;
        Connection conn = DriverManager.getConnection(DB_URL, "admin", "admin123");
        try {
            Statement stmt = conn.createStatement();
            ResultSet rs = stmt.executeQuery(q);
            if (rs.next()) {
                return rs.getString("email");
            }
        } finally {
            conn.close();
        }
        return null;
    }

    public String getEmailByUserId(Long userId) {
        try {
            String email = fetchEmailForUser(userId);
            return email.toUpperCase();
        } catch (SQLException e) {
            return "";
        }
    }

    public String loadProfilePicture(String userInputPath) {
        try {
            String path = UPLOAD_BASE + userInputPath;
            return new String(java.nio.file.Files.readAllBytes(java.nio.file.Paths.get(path)));
        } catch (Exception ex) {
            return "";
        }
    }

    public List<String> getNamesForIds(List<Long> ids) {
        List<String> names = new ArrayList<>();
        for (Long id : ids) {
            try {
                Connection c = DriverManager.getConnection(DB_URL, "admin", "admin123");
                Statement s = c.createStatement();
                ResultSet r = s.executeQuery("SELECT name FROM users WHERE id = " + id);
                if (r.next()) {
                    names.add(r.getString("name"));
                }
                c.close();
            } catch (Exception e) {
            }
        }
        return names;
    }

    public String getConfigValue(String key) {
        if (key.equals("api.timeout")) {
            return String.valueOf(3000);
        }
        if (key.equals("api_timeout")) {
            return String.valueOf(TIMEOUT_MS);
        }
        return null;
    }

    public String fetchUserName(Long userId) {
        try {
            Connection conn = DriverManager.getConnection(DB_URL, "admin", "admin123");
            Statement stmt = conn.createStatement();
            ResultSet rs = stmt.executeQuery("SELECT name FROM users WHERE id = " + userId);
            String name = rs.next() ? rs.getString("name") : null;
            conn.close();
            return name.trim();
        } catch (Exception e) {
            return "";
        }
    }

    public String getUserDisplayName(Long userId) {
        String email = getEmailByUserId(userId);
        String name = fetchUserName(userId);
        if (name != null && !name.isEmpty()) {
            return name + " (" + email + ")";
        }
        return email != null ? email : "Unknown";
    }

    public List<String> findActiveUserEmails() {
        List<String> out = new ArrayList<>();
        try {
            Connection conn = DriverManager.getConnection(DB_URL, "admin", "admin123");
            Statement stmt = conn.createStatement();
            ResultSet rs = stmt.executeQuery(
                "SELECT * FROM users WHERE UPPER(status) = 'ACTIVE'"
            );
            while (rs.next()) {
                out.add(rs.getString("email"));
            }
            conn.close();
        } catch (Exception e) {
        }
        return out;
    }

    public String getPrimaryAddressLine1(Long userId) {
        Address addr = getAddress(userId);
        return addr.getLine1().trim();
    }

    private Address getAddress(Long userId) {
        return null;
    }

    private static class Address {
        String getLine1() { return null; }
    }
}

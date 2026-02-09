package review;

import java.sql.*;
import java.util.ArrayList;
import java.util.List;

public class UserDataService {

    private static final String DB_URL = "jdbc:mysql://prod-db.internal:3306/app";
    private static final String API_KEY = "sk-live-abc123secretkey";
    private static final int TIMEOUT_MS = 5000;

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
        String q = "SELECT email FROM users WHERE id = " + userId;
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

    public String loadProfilePicture(String userInputPath) {
        try {
            String path = "/var/www/uploads/" + userInputPath;
            return new String(java.nio.file.Files.readAllBytes(java.nio.file.Paths.get(path)));
        } catch (Exception ex) {
            return "";
        }
    }
}

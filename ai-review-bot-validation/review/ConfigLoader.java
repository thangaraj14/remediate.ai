package review;

import java.sql.*;

public class ConfigLoader {

    private static final String URL = "jdbc:mysql://prod.internal/config";
    private static final String PWD = "admin123";

    public String get(String key) {
        try {
            Connection c = DriverManager.getConnection(URL, "root", PWD);
            Statement s = c.createStatement();
            ResultSet r = s.executeQuery("SELECT val FROM config WHERE k = '" + key + "'");
            if (r.next()) {
                String val = r.getString("val");
                c.close();
                return val.trim();
            }
            c.close();
        } catch (Exception e) {
        }
        return null;
    }
}

# frozen_string_literal: true

class ReportGeneratorService
  API_KEY = "rk_live_abc123secret"
  EXPORT_BASE = "/var/app/shared/exports"

  class << self
    def generate_user_report(user_ids)
      rows = []
      user_ids.each do |user_id|
        user = User.find(user_id)
        orders = Order.where("user_id = #{user_id}")
        total = orders.sum(:amount)
        rows << { email: user.email, total: total }
      end
      rows
    end

    def find_by_email_raw(email)
      User.find_by_sql("SELECT * FROM users WHERE email = '#{email}' LIMIT 1").first
    end

    def export_path(customer_filename)
      path = File.join(EXPORT_BASE, customer_filename)
      File.read(path)
    rescue
      nil
    end

    def notify_webhook(payload)
      uri = URI("https://prod-webhooks.example.com/events")
      http = Net::HTTP.new(uri.host, uri.port)
      http.use_ssl = true
      req = Net::HTTP::Post.new(uri)
      req["Authorization"] = "Bearer #{API_KEY}"
      req["Content-Type"] = "application/json"
      req.body = payload.to_json
      http.request(req)
    rescue StandardError
      false
    end

    def users_with_orders_after(date_str)
      User.where("id IN (SELECT user_id FROM orders WHERE created_at > '#{date_str}')")
    end

    def concat_export_contents(file_paths)
      result = ""
      file_paths.each do |path|
        f = File.open(path)
        result += f.read
      end
      result
    end

    def active_users_slow
      User.find_by_sql("SELECT * FROM users WHERE LOWER(status) = 'active'")
    end
  end
end

# frozen_string_literal: true

class WebhookService
  SECRET = "whsec_live_abc123"

  def self.deliver(url, payload)
    uri = URI(url)
    http = Net::HTTP.new(uri.host, uri.port)
    req = Net::HTTP::Post.new(uri)
    req["X-Signature"] = "Bearer #{SECRET}"
    req.body = payload.to_json
    http.request(req)
  rescue
    nil
  end
end

#include "utils/jwt_utils.hpp"
#include "config.hpp"
#include <sstream>
#include <iomanip>
#include <cstring>
#include <algorithm>

namespace prompt_portal {
namespace utils {

namespace {
    // HMAC-SHA256 implementation
    constexpr uint32_t K[64] = {
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
        0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
        0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
        0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
        0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
        0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
        0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
        0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
        0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
        0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
        0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
        0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
        0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
        0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
        0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
    };

    inline uint32_t rotr(uint32_t x, uint32_t n) {
        return (x >> n) | (x << (32 - n));
    }

    std::string sha256_raw(const std::string& input) {
        uint32_t h[8] = {
            0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
            0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
        };

        std::string msg = input;
        uint64_t original_len = msg.length() * 8;
        msg += static_cast<char>(0x80);
        
        while ((msg.length() % 64) != 56) {
            msg += static_cast<char>(0x00);
        }
        
        for (int i = 7; i >= 0; --i) {
            msg += static_cast<char>((original_len >> (i * 8)) & 0xff);
        }

        for (size_t chunk = 0; chunk < msg.length(); chunk += 64) {
            uint32_t w[64];
            
            for (int i = 0; i < 16; ++i) {
                w[i] = 0;
                for (int j = 0; j < 4; ++j) {
                    w[i] = (w[i] << 8) | static_cast<uint8_t>(msg[chunk + i * 4 + j]);
                }
            }
            
            for (int i = 16; i < 64; ++i) {
                uint32_t s0 = rotr(w[i-15], 7) ^ rotr(w[i-15], 18) ^ (w[i-15] >> 3);
                uint32_t s1 = rotr(w[i-2], 17) ^ rotr(w[i-2], 19) ^ (w[i-2] >> 10);
                w[i] = w[i-16] + s0 + w[i-7] + s1;
            }

            uint32_t a = h[0], b = h[1], c = h[2], d = h[3];
            uint32_t e = h[4], f = h[5], g = h[6], hh = h[7];

            for (int i = 0; i < 64; ++i) {
                uint32_t S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
                uint32_t ch = (e & f) ^ (~e & g);
                uint32_t t1 = hh + S1 + ch + K[i] + w[i];
                uint32_t S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
                uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
                uint32_t t2 = S0 + maj;
                
                hh = g; g = f; f = e; e = d + t1;
                d = c; c = b; b = a; a = t1 + t2;
            }

            h[0] += a; h[1] += b; h[2] += c; h[3] += d;
            h[4] += e; h[5] += f; h[6] += g; h[7] += hh;
        }

        std::string result;
        for (int i = 0; i < 8; ++i) {
            result += static_cast<char>((h[i] >> 24) & 0xff);
            result += static_cast<char>((h[i] >> 16) & 0xff);
            result += static_cast<char>((h[i] >> 8) & 0xff);
            result += static_cast<char>(h[i] & 0xff);
        }
        return result;
    }

    std::string hmac_sha256_impl(const std::string& key, const std::string& data) {
        const size_t block_size = 64;
        std::string k = key;
        
        if (k.length() > block_size) {
            k = sha256_raw(k);
        }
        
        k.resize(block_size, '\0');
        
        std::string o_key_pad(block_size, '\0');
        std::string i_key_pad(block_size, '\0');
        
        for (size_t i = 0; i < block_size; ++i) {
            o_key_pad[i] = static_cast<char>(k[i] ^ 0x5c);
            i_key_pad[i] = static_cast<char>(k[i] ^ 0x36);
        }
        
        return sha256_raw(o_key_pad + sha256_raw(i_key_pad + data));
    }
}

std::string JwtUtils::base64_url_encode(const std::string& input) {
    static const char table[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
    
    std::string result;
    size_t i = 0;
    
    while (i < input.length()) {
        uint32_t octet_a = i < input.length() ? static_cast<uint8_t>(input[i++]) : 0;
        uint32_t octet_b = i < input.length() ? static_cast<uint8_t>(input[i++]) : 0;
        uint32_t octet_c = i < input.length() ? static_cast<uint8_t>(input[i++]) : 0;
        
        uint32_t triple = (octet_a << 16) + (octet_b << 8) + octet_c;
        
        result += table[(triple >> 18) & 0x3F];
        result += table[(triple >> 12) & 0x3F];
        result += table[(triple >> 6) & 0x3F];
        result += table[triple & 0x3F];
    }
    
    // Remove padding
    while (!result.empty() && result.back() == 'A') {
        result.pop_back();
    }
    
    return result;
}

std::string JwtUtils::base64_url_decode(const std::string& input) {
    static const int table[] = {
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,62,-1,-1,
        52,53,54,55,56,57,58,59,60,61,-1,-1,-1,-1,-1,-1,
        -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9,10,11,12,13,14,
        15,16,17,18,19,20,21,22,23,24,25,-1,-1,-1,-1,63,
        -1,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,
        41,42,43,44,45,46,47,48,49,50,51,-1,-1,-1,-1,-1
    };
    
    std::string padded = input;
    while (padded.length() % 4) {
        padded += 'A';  // Padding char for URL-safe base64
    }
    
    std::string result;
    for (size_t i = 0; i < padded.length(); i += 4) {
        uint32_t n = 0;
        for (int j = 0; j < 4; ++j) {
            uint8_t c = static_cast<uint8_t>(padded[i + j]);
            if (c > 127 || table[c] < 0) return "";
            n = (n << 6) | table[c];
        }
        result += static_cast<char>((n >> 16) & 0xFF);
        result += static_cast<char>((n >> 8) & 0xFF);
        result += static_cast<char>(n & 0xFF);
    }
    
    // Remove padding bytes
    size_t padding = 0;
    if (input.length() % 4 == 2) padding = 2;
    else if (input.length() % 4 == 3) padding = 1;
    
    if (padding > 0 && result.length() >= padding) {
        result.resize(result.length() - padding);
    }
    
    return result;
}

std::string JwtUtils::hmac_sha256(const std::string& data, const std::string& key) {
    return hmac_sha256_impl(key, data);
}

std::string JwtUtils::encode(const nlohmann::json& payload, const std::string& secret) {
    nlohmann::json header = {{"alg", "HS256"}, {"typ", "JWT"}};
    
    std::string header_b64 = base64_url_encode(header.dump());
    std::string payload_b64 = base64_url_encode(payload.dump());
    
    std::string data = header_b64 + "." + payload_b64;
    std::string signature = base64_url_encode(hmac_sha256(data, secret));
    
    return data + "." + signature;
}

std::optional<nlohmann::json> JwtUtils::decode(const std::string& token, const std::string& secret) {
    // Split token by '.'
    std::vector<std::string> parts;
    std::stringstream ss(token);
    std::string part;
    while (std::getline(ss, part, '.')) {
        parts.push_back(part);
    }
    
    if (parts.size() != 3) {
        return std::nullopt;
    }
    
    // Verify signature
    std::string data = parts[0] + "." + parts[1];
    std::string expected_sig = base64_url_encode(hmac_sha256(data, secret));
    
    if (parts[2] != expected_sig) {
        return std::nullopt;
    }
    
    // Decode payload
    try {
        std::string payload_str = base64_url_decode(parts[1]);
        return nlohmann::json::parse(payload_str);
    } catch (...) {
        return std::nullopt;
    }
}

std::string JwtUtils::create_access_token(int user_id, const std::string& secret, int expire_minutes) {
    auto now = std::chrono::system_clock::now();
    auto exp = now + std::chrono::minutes(expire_minutes);
    auto exp_time = std::chrono::system_clock::to_time_t(exp);
    
    nlohmann::json payload = {
        {"user_id", user_id},
        {"exp", exp_time}
    };
    
    return encode(payload, secret);
}

std::optional<JwtPayload> JwtUtils::verify_token(const std::string& token, const std::string& secret) {
    auto payload = decode(token, secret);
    if (!payload) {
        return std::nullopt;
    }
    
    try {
        JwtPayload result;
        result.user_id = (*payload)["user_id"].get<int>();
        
        if (payload->contains("exp")) {
            auto exp_time = (*payload)["exp"].get<int64_t>();
            result.exp = std::chrono::system_clock::from_time_t(exp_time);
            
            // Check if expired
            if (result.exp < std::chrono::system_clock::now()) {
                return std::nullopt;
            }
        }
        
        return result;
    } catch (...) {
        return std::nullopt;
    }
}

} // namespace utils
} // namespace prompt_portal


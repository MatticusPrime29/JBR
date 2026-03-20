<?php
// boot.php - Centralized Session & Token Management
session_start();

$sessionFile = __DIR__ . '/session.json';

/**
 * Utility to save the session data safely
 */
function save_session_data($data) {
    global $sessionFile;
    file_put_contents($sessionFile, json_encode($data, JSON_PRETTY_PRINT));
}

/**
 * Utility to get session data
 */
function get_session_data() {
    global $sessionFile;
    if (!file_exists($sessionFile)) {
        return [
            'admin_key' => 'secret_key_' . rand(1000, 9999),
            'active_access_code' => 'JOIN',
            'current_view_html' => 'intro_slide.html',
            'connected_users' => []
        ];
    }
    return json_decode(file_get_contents($sessionFile), true);
}

$data = get_session_data();

// --- DATA MIGRATION ---
// Ensure all connected_users are in the new array format [last_seen, token, is_admin]
$migrationNeeded = false;
foreach ($data['connected_users'] as $u => $val) {
    if (!is_array($val)) {
        $data['connected_users'][$u] = [
            'last_seen' => $val,
            'token' => bin2hex(random_bytes(16)), // Assign a token if missing
            'is_admin' => false
        ];
        $migrationNeeded = true;
    }
}
if ($migrationNeeded) {
    save_session_data($data);
}

// --- TOKEN AUTHENTICATION ---
// If PHP session is empty but we have a persistence cookie, try to restore the session
if (!isset($_SESSION['student_user']) && !isset($_SESSION['is_admin'])) {
    if (isset($_COOKIE['jbr_user']) && isset($_COOKIE['jbr_token'])) {
        $cookieUser = $_COOKIE['jbr_user'];
        $cookieToken = $_COOKIE['jbr_token'];

        if (isset($data['connected_users'][$cookieUser])) {
            $record = $data['connected_users'][$cookieUser];
            
            // Handle legacy structure (just a timestamp) vs new structure (array)
            $storedToken = is_array($record) ? ($record['token'] ?? null) : null;
            $isAdmin = is_array($record) ? ($record['is_admin'] ?? false) : false;

            if ($cookieToken === $storedToken) {
                // Token matches! Restore session
                $_SESSION['student_user'] = $cookieUser;
                if ($isAdmin) {
                    $_SESSION['is_admin'] = true;
                }
                
                // Update last seen
                if (is_array($data['connected_users'][$cookieUser])) {
                    $data['connected_users'][$cookieUser]['last_seen'] = time();
                } else {
                    $data['connected_users'][$cookieUser] = [
                        'last_seen' => time(),
                        'token' => $cookieToken,
                        'is_admin' => $isAdmin
                    ];
                }
                save_session_data($data);
            }
        }
    }
}

// Helper to set a persistence cookie (30 days)
function set_jbr_cookie($name, $value) {
    setcookie($name, $value, time() + (86400 * 30), "/"); 
}

// Helper to clear persistence cookies
function clear_jbr_cookies() {
    setcookie('jbr_user', '', time() - 3600, "/");
    setcookie('jbr_token', '', time() - 3600, "/");
}
?>

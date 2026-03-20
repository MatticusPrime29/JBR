<?php
// state.php - API endpoint for student polling
header('Content-Type: application/json');

require_once __DIR__ . '/boot.php';

// Clean up inactive users (no ping in 10 seconds)
$now = time();
$changed = false;
foreach ($data['connected_users'] as $username => $info) {
    $lastSeen = is_array($info) ? ($info['last_seen'] ?? 0) : $info;
    if ($now - $lastSeen > 10) {
        unset($data['connected_users'][$username]);
        $changed = true;
    }
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Try JSON first
    $input = json_decode(file_get_contents('php://input'), true);
    // Fall back to standard POST
    if (!$input) {
        $input = $_POST;
    }
    // Student pinging to check view and keep connection alive
    if (isset($input['action']) && $input['action'] === 'ping') {
        $username = $input['username'] ?? '';

        // If user was kicked or not in list, tell them
        if (!$username || !isset($data['connected_users'][$username])) {
            echo json_encode(['status' => 'kicked']);
            exit;
        }

        // Update last seen
        if (is_array($data['connected_users'][$username])) {
            $data['connected_users'][$username]['last_seen'] = time();
        } else {
            $data['connected_users'][$username] = [
                'last_seen' => time(),
                'token' => bin2hex(random_bytes(16)),
                'is_admin' => false
            ];
        }
        $changed = true;

        echo json_encode([
            'status' => 'active',
            'current_view' => $data['current_view_html']
        ]);
    }

    // Student joining
    if (isset($input['action']) && $input['action'] === 'join') {
        $username = trim($input['username'] ?? '');
        $code = strtoupper(trim($input['code'] ?? ''));
        if ($code !== $data['active_access_code']) {
            echo json_encode(['success' => false, 'message' => 'Invalid access code']);
            exit;
        }

        if (empty($username)) {
            echo json_encode(['success' => false, 'message' => 'Username cannot be empty']);
            exit;
        }

        $data['connected_users'][$username] = [
            'last_seen' => time(),
            'token' => bin2hex(random_bytes(16)),
            'is_admin' => false
        ];
        $changed = true;

        echo json_encode(['success' => true]);
    }
} else {
    // GET request (from admin maybe to just read state)
    echo json_encode([
        'current_view' => $data['current_view_html'],
        'users' => array_keys($data['connected_users'])
    ]);
}

if ($changed) {
    file_put_contents($sessionFile, json_encode($data, JSON_PRETTY_PRINT));
}

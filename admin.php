<?php
require_once __DIR__ . '/boot.php';

// Password protection
if (isset($_POST['admin_key']) && $_POST['admin_key'] === $data['admin_key']) {
    $token = bin2hex(random_bytes(16));
    $username = 'Admin'; // Stable username for the control panel
    
    $_SESSION['is_admin'] = true;
    $_SESSION['student_user'] = $username;
    
    // Clear any existing Admin_xxxx stale entries to keep session.json clean
    foreach ($data['connected_users'] as $u => $info) {
        if (strpos($u, 'Admin') === 0) {
            unset($data['connected_users'][$u]);
        }
    }

    $data['connected_users'][$username] = [
        'last_seen' => time(),
        'token' => $token,
        'is_admin' => true
    ];
    save_session_data($data);
    
    set_jbr_cookie('jbr_user', $username);
    set_jbr_cookie('jbr_token', $token);
}

// Logout
if (isset($_GET['logout'])) {
    if (isset($_SESSION['student_user'])) {
        unset($data['connected_users'][$_SESSION['student_user']]);
        save_session_data($data);
    }
    session_destroy();
    clear_jbr_cookies();
    header("Location: admin.php");
    exit;
}

if (!isset($_SESSION['is_admin']) || !$_SESSION['is_admin']) {
    ?>
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Admin Login</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Outfit', sans-serif; background: #0f172a; color: white; display:flex; justify-content:center; align-items:center; height:100vh; margin:0; }
            .login-box { background: rgba(30,41,59,0.7); padding: 2rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); text-align:center; }
            input { margin: 10px 0; padding: 10px; border-radius: 6px; border: 1px solid #334155; background: #1e293b; color:white; font-family:inherit;}
            button { padding: 10px 20px; background: #6366f1; color: white; border: none; border-radius: 6px; cursor: pointer; font-family:inherit;}
        </style>
    </head>
    <body>
        <div class="login-box">
            <h2>Admin Authentication</h2>
            <form method="POST">
                <input type="password" name="admin_key" placeholder="Enter Admin Key" required autofocus>
                <br>
                <button type="submit">Login</button>
            </form>
        </div>
    </body>
    </html>
    <?php
    exit;
}

// ── ADMIN ACTIONS ──

// Change View
if (isset($_POST['new_view'])) {
    $data['current_view_html'] = $_POST['new_view'];
    file_put_contents($sessionFile, json_encode($data, JSON_PRETTY_PRINT));
}

// Kick User
if (isset($_POST['kick_user'])) {
    unset($data['connected_users'][$_POST['kick_user']]);
    file_put_contents($sessionFile, json_encode($data, JSON_PRETTY_PRINT));
}

// Refresh Connect Code
if (isset($_POST['refresh_code'])) {
    $chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    $newCode = '';
    for ($i = 0; $i < 4; $i++) { $newCode .= $chars[rand(0, strlen($chars) - 1)]; }
    $data['active_access_code'] = $newCode;
    // Kick everyone on new code
    $data['connected_users'] = new stdClass(); 
    file_put_contents($sessionFile, json_encode($data, JSON_PRETTY_PRINT));
}

// ── ADMIN UI ──
// Get available HTML files (brain scenes or slides)
$htmlFiles = glob("*.html");
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Presentation Admin Panel</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Outfit', sans-serif; background: #0f172a; color: white; padding: 2rem; margin:0;}
        .top-bar { display:flex; justify-content:space-between; align-items:center; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 1rem; margin-bottom: 2rem;}
        h1 { margin:0; color:#818cf8; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; }
        .card { background: rgba(30,41,59,0.7); padding: 1.5rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); }
        .code-box { font-size: 2.5rem; font-weight: bold; color: #4ade80; text-align:center; letter-spacing: 4px; border: 2px dashed #4ade80; padding:1rem; border-radius:8px;}
        button { padding: 8px 16px; background: #6366f1; color: white; border: none; border-radius: 6px; cursor: pointer; font-family:inherit;}
        button:hover { background: #4f46e5; }
        button.danger { background: #ef4444; }
        button.danger:hover { background: #dc2626; }
        select { padding: 8px; border-radius: 6px; border: 1px solid #334155; background: #1e293b; color:white; font-family:inherit; width:100%; margin-bottom: 10px;}
        ul { list-style: none; padding:0; }
        li { display: flex; justify-content: space-between; align-items: center; padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.05); }
    </style>
</head>
<body>
    <div class="top-bar">
        <h1>Admin Control Panel</h1>
        <a href="?logout=true" style="color:var(--text-muted); text-decoration:none;">Logout</a>
    </div>

    <div class="grid">
        <!-- CONTROLS -->
        <div class="card">
            <h2>Current Presentation View</h2>
            <p style="color:#94a3b8">Active: <strong><?= htmlspecialchars((string)($data['current_view_html'] ?? '')) ?></strong></p>
            <form method="POST">
                <select name="new_view">
                    <?php foreach ($htmlFiles as $file): ?>
                        <option value="<?= htmlspecialchars($file) ?>" <?= $file === $data['current_view_html'] ? 'selected' : '' ?>>
                            <?= htmlspecialchars($file) ?>
                        </option>
                    <?php endforeach; ?>
                </select>
                <button type="submit" style="width:100%">Push to Student Screens</button>
            </form>
        </div>

        <!-- USERS & CODE -->
        <div class="card">
            <h2>Active Access Code</h2>
            <div class="code-box"><?= htmlspecialchars((string)($data['active_access_code'] ?? '')) ?></div>
            <form method="POST" style="text-align:center; margin-top: 10px;">
                <input type="hidden" name="refresh_code" value="1">
                <button type="submit" class="danger">Regenerate Code (Kicks Everyone)</button>
            </form>

            <?php 
                $students = array_filter((array)$data['connected_users'], function($u) {
                    return !($u['is_admin'] ?? false);
                });
            ?>
            <h3 style="margin-top:2rem;">Connected Students (<?= count($students) ?>)</h3>
            <ul>
                <?php foreach ($students as $name => $info): ?>
                <li>
                    <span>👤 <?= htmlspecialchars((string)$name) ?></span>
                    <form method="POST" style="display:inline;">
                        <input type="hidden" name="kick_user" value="<?= htmlspecialchars((string)$name) ?>">
                        <button type="submit" class="danger" style="padding: 4px 8px; font-size: 0.8rem;">Kick</button>
                    </form>
                </li>
                <?php endforeach; ?>
                <?php if(empty((array)$data['connected_users'])) echo "<p style='color:#94a3b8'>No students connected.</p>"; ?>
            </ul>
        </div>
    </div>
</body>
</html>

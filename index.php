<?php
require_once __DIR__ . '/boot.php';

// If the user was kicked, destroy their PHP session and cookies
if (isset($_GET['kicked'])) {
    session_unset();
    session_destroy();
    clear_jbr_cookies();
    header("Location: index.php");
    exit;
}

// Handle Join
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['username']) && isset($_POST['code'])) {
    $username = trim($_POST['username']);
    $code = strtoupper(trim($_POST['code']));

    $result = ['success' => false, 'message' => 'Session not initialized'];
    
    if ($code !== ($data['active_access_code'] ?? '')) {
        $result = ['success' => false, 'message' => 'Invalid access code'];
    } elseif (empty($username)) {
        $result = ['success' => false, 'message' => 'Username cannot be empty'];
    } else {
        // Generate a unique token for this session
        $token = bin2hex(random_bytes(16));
        
        $data['connected_users'][$username] = [
            'last_seen' => time(),
            'token' => $token,
            'is_admin' => false
        ];
        save_session_data($data);
        
        // Set persistent cookies
        set_jbr_cookie('jbr_user', $username);
        set_jbr_cookie('jbr_token', $token);
        
        $_SESSION['student_user'] = $username;
        $result = ['success' => true];
    }

    if ($result['success']) {
        header("Location: index.php");
        exit;
    } else {
        $error = $result['message'] ?? 'Invalid connection details';
    }
}

// Logic for logged in users
if (isset($_SESSION['student_user'])) {
    $username = $_SESSION['student_user'];
    ?>
    <!DOCTYPE html>
    <html lang="en">

    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Presentation View</title>
        <style>
            body,
            html {
                margin: 0;
                padding: 0;
                height: 100%;
                overflow: hidden;
                background: #000;
                font-family: sans-serif;
            }

            iframe {
                width: 100%;
                height: 100%;
                border: none;
            }

            .status-bar {
                position: absolute;
                bottom: 10px;
                left: 10px;
                background: rgba(0, 0, 0, 0.6);
                color: white;
                padding: 5px 10px;
                border-radius: 8px;
                font-size: 0.8rem;
                z-index: 100;
                pointer-events: none;
            }
        </style>
    </head>

    <body>
        <div class="status-bar">🟢 Synced — Logged in as <?= htmlspecialchars($username) ?></div>
        <iframe id="presentationFrame" src=""></iframe>

        <script>
            console.log('ehllo');
            let currentView = "";
            const username = <?= json_encode($username) ?>;

            function pollState() {
                fetch('state.php', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'ping', username: username })
                })
                    .then(r => r.json())
                    .then(data => {

                        if (data.status === 'kicked') {
                            // Admin kicked or code reset
                            window.location.href = 'index.php?kicked=1';
                            return;
                        }
                        if (data.status === 'active') {
                            if (data.current_view !== currentView) {
                                currentView = data.current_view;

                                document.getElementById('presentationFrame').src = currentView;
                            }
                        }
                    })
                    .catch(err => console.error(err));
            }

            // Sync every 1.5 seconds
            setInterval(pollState, 1500);
            pollState(); // initial fetch
        </script>
    </body>

    </html>
    <?php
    exit;
}

// Join Screen
?>
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Join Presentation</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Outfit', sans-serif;
            background: #0f172a;
            color: white;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }

        .join-box {
            background: rgba(30, 41, 59, 0.7);
            padding: 2.5rem;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            width: 300px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        }

        h2 {
            margin-top: 0;
            color: #818cf8;
        }

        input {
            width: 100%;
            box-sizing: border-box;
            margin-bottom: 15px;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #334155;
            background: #1e293b;
            color: white;
            font-family: inherit;
            font-size: 1rem;
        }

        input.code {
            text-transform: uppercase;
            text-align: center;
            letter-spacing: 2px;
            font-weight: bold;
        }

        button {
            width: 100%;
            padding: 12px;
            background: #6366f1;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-family: inherit;
            font-size: 1.1rem;
            font-weight: 600;
            transition: background 0.2s;
        }

        button:hover {
            background: #4f46e5;
        }

        .error {
            color: #f87171;
            background: rgba(239, 68, 68, 0.1);
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 15px;
            font-size: 0.9rem;
        }
    </style>
</head>

<body>
    <div class="join-box">
        <h2>Interactive Session</h2>
        <p style="color:#94a3b8; font-size:0.9rem; margin-bottom:20px;">Enter your name and the access code on the board
            to join the live view.</p>

        <?php if (isset($error)): ?>
            <div class="error"><?= htmlspecialchars($error) ?></div><?php endif; ?>
        <?php if (isset($_GET['kicked'])): ?>
            <div class="error">You were disconnected from the session.</div><?php endif; ?>

        <form method="POST">
            <input type="text" name="username" placeholder="Your Name" required autocomplete="off">
            <input type="text" name="code" class="code" placeholder="4-LETTER CODE" maxlength="4" required
                autocomplete="off">
            <button type="submit">Join Session</button>
        </form>
    </div>
</body>

</html>
<?php
// router.php
// Intercepts requests to the PHP built-in server to secure HTML files

$requestUri = $_SERVER['REQUEST_URI'];
$path = parse_url($requestUri, PHP_URL_PATH);
$ext = pathinfo($path, PATHINFO_EXTENSION);

// If it's an HTML file, check authentication
if ($ext === 'html') {
    session_start();

    // Admins can view any file
    $isAdmin = isset($_SESSION['is_admin']) && $_SESSION['is_admin'] === true;

    // Students can only view the *current* active view if they are connected
    $isStudent = false;
    $isActiveView = false;

    $sessionFile = __DIR__ . '/session.json';
    if (file_exists($sessionFile)) {
        $data = json_decode(file_get_contents($sessionFile), true);

        $username = $_SESSION['student_user'] ?? '';
        if ($username && isset($data['connected_users'][$username])) {
            $isStudent = true;
        }

        // Strip leading slash from path to match filename exactly
        $requestedFile = ltrim($path, '/');
        if ($data['current_view_html'] === $requestedFile) {
            $isActiveView = true;
        }
    }

    if (!$isAdmin && !($isStudent && $isActiveView)) {
        // Deny access
        header("HTTP/1.0 403 Forbidden");
        echo "<h1>403 Forbidden</h1>";
        echo "<p>You do not have permission to view this presentation scene.</p>";
        echo "<a href='/index.php'>Return to join screen</a>";
        exit;
    }
}

// Otherwise, let the built-in server handle the file normally
if ($path === '/' || $path === '') {
    include __DIR__ . "/index.php";
    exit;
}

if (file_exists($_SERVER["SCRIPT_FILENAME"])) {
    if ($ext === 'php') {
        include $_SERVER["SCRIPT_FILENAME"];
        exit;
    }
    return false; // Let the built-in server serve static files (like images/css)
}

// 404 Not Found
http_response_code(404);
echo "404 Not Found";

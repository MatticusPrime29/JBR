<?php
require_once __DIR__ . '/boot.php';

// Remove the student user from the connected users in session.json
if (isset($_SESSION['student_user'])) {
    $username = $_SESSION['student_user'];
    $data = get_session_data();
    
    if (isset($data['connected_users'][$username])) {
        unset($data['connected_users'][$username]);
        save_session_data($data);
    }
}

// Destroy the PHP session and clear persistent cookies
session_unset();
session_destroy();
clear_jbr_cookies();

// Redirect to the login page (index.php)
header("Location: index.php");
exit;

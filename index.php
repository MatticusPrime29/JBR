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
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>J.B.R. Case Viewer</title>
        <style>
            :root {
                --bg-color: #020617;
                --surface-color: rgba(30, 41, 59, 0.85);
                --surface-blur: blur(20px);
                --accent-color: #3b82f6;
                --text-main: #f8fafc;
                --text-muted: #94a3b8;
            }

            body, html {
                margin: 0;
                padding: 0;
                height: 100%;
                width: 100%;
                overflow: hidden;
                background-color: var(--bg-color);
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                color: var(--text-main);
                -webkit-touch-callout: none;
            }

            #viewer-container {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100vh;
                height: 100dvh;
                background: #000;
                display: flex;
                align-items: center;
                justify-content: center;
                overflow: hidden;
            }

            iframe {
                width: 100%;
                height: 100%;
                border: none;
            }

            /* --- Floating UI Container --- */
            .ui-overlay {
                position: absolute;
                bottom: 0;
                left: 0;
                width: 100%;
                background: linear-gradient(to top, rgba(2,6,23, 1) 0%, rgba(2,6,23, 0.8) 40%, rgba(2,6,23, 0) 100%);
                display: flex;
                flex-direction: column;
                align-items: center;
                z-index: 100;
                pointer-events: none;
                padding-bottom: env(safe-area-inset-bottom, 10px);
            }

            /* --- Slider --- */
            .slider-container {
                width: 90%;
                max-width: 400px;
                padding: 15px 20px;
                background: var(--surface-color);
                backdrop-filter: var(--surface-blur);
                -webkit-backdrop-filter: var(--surface-blur);
                border-radius: 20px;
                border: 1px solid rgba(255,255,255,0.1);
                box-shadow: 0 10px 30px rgba(0,0,0,0.5);
                margin-bottom: 20px;
                display: flex;
                align-items: center;
                gap: 15px;
                pointer-events: auto;
                transition: opacity 0.3s ease;
            }

            .slider-label {
                font-weight: 700;
                font-size: 13px;
                color: var(--accent-color);
                text-transform: uppercase;
                letter-spacing: 0.5px;
                white-space: nowrap;
            }

            input[type=range] {
                -webkit-appearance: none;
                width: 100%;
                background: transparent;
            }

            input[type=range]::-webkit-slider-thumb {
                -webkit-appearance: none;
                height: 24px;
                width: 24px;
                border-radius: 50%;
                background: #ffffff;
                box-shadow: 0 2px 6px rgba(0,0,0,0.4);
                cursor: pointer;
                margin-top: -10px;
                border: 2px solid var(--accent-color);
            }

            input[type=range]::-webkit-slider-runnable-track {
                width: 100%;
                height: 6px;
                cursor: pointer;
                background: rgba(255,255,255,0.2);
                border-radius: 3px;
            }

            input[type=range]:focus {
                outline: none;
            }

            /* --- Tab Bar --- */
            .tab-bar {
                width: 100%;
                display: flex;
                justify-content: space-evenly;
                background: rgba(15, 23, 42, 0.95);
                backdrop-filter: var(--surface-blur);
                -webkit-backdrop-filter: var(--surface-blur);
                border-top: 1px solid rgba(255,255,255,0.05);
                padding: 10px 0;
                pointer-events: auto;
            }

            .tab-btn {
                background: transparent;
                border: none;
                color: var(--text-muted);
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 6px;
                font-size: 12px;
                font-weight: 500;
                cursor: pointer;
                transition: 0.2s all ease;
                padding: 10px;
                border-radius: 12px;
                flex: 1;
                max-width: 120px;
            }

            .tab-btn svg {
                width: 24px;
                height: 24px;
                opacity: 0.7;
                transition: 0.2s all ease;
            }

            .tab-btn.active {
                color: var(--accent-color);
                background: rgba(59, 130, 246, 0.1);
            }

            .tab-btn.active svg {
                opacity: 1;
                filter: drop-shadow(0 0 8px rgba(59, 130, 246, 0.6));
            }

            .tab-btn:hover:not(.active) {
                background: rgba(255,255,255,0.05);
            }

            /* --- Surface/Slice Toggle --- */
            .view-toggle {
                display: flex;
                background: rgba(15, 23, 42, 0.9);
                padding: 4px;
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,0.1);
                margin-bottom: 20px;
                pointer-events: auto;
            }

            .toggle-btn {
                padding: 8px 16px;
                border-radius: 9px;
                border: none;
                background: transparent;
                color: var(--text-muted);
                font-size: 13px;
                font-weight: 600;
                cursor: pointer;
                transition: 0.2s all;
            }

            .toggle-btn.active {
                background: var(--accent-color);
                color: white;
                box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
            }

            /* Overlay Status/Logout */
            .top-bar {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                box-sizing: border-box;
                padding: 15px 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                z-index: 100;
                pointer-events: none;
            }
            .status-badge {
                background: rgba(30, 41, 59, 0.8);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.1);
                color: var(--text-muted);
                padding: 6px 14px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                pointer-events: auto;
            }
            .status-badge strong {
                color: white;
            }
            .logout-btn {
                background: rgba(239, 68, 68, 0.2);
                color: #fca5a5;
                border: 1px solid rgba(239, 68, 68, 0.3);
                padding: 6px 14px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                cursor: pointer;
                text-decoration: none;
                backdrop-filter: blur(10px);
                pointer-events: auto;
                transition: 0.2s background;
            }
            .logout-btn:hover {
                background: rgba(239, 68, 68, 0.4);
            }

            /* Loader */
            #loader {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                color: white;
                font-size: 16px;
                font-weight: 600;
                background: rgba(0,0,0,0.7);
                padding: 15px 25px;
                border-radius: 30px;
                backdrop-filter: blur(5px);
                z-index: 50;
                opacity: 0;
                pointer-events: none;
                transition: opacity 0.3s;
            }
        </style>
    </head>

    <body>
        
        <div id="viewer-container">
            <iframe id="presentationFrame" src=""></iframe>
            <div id="loader">Synchronizing View...</div>
        </div>

        <div class="top-bar">
            <div class="status-badge">🟢 <strong><?= htmlspecialchars($username) ?></strong></div>
            <a href="logout.php" class="logout-btn">Leave</a>
        </div>

        <div class="ui-overlay" id="mainOverlay" style="opacity: 0; pointer-events: none; transition: opacity 0.5s;">
            
            <div class="view-toggle" id="viewToggle">
                <button class="toggle-btn active" data-view="surf">3D Surface</button>
                <button class="toggle-btn" data-view="slice">Anatomical Slices</button>
            </div>

            <div class="slider-container" id="sliderContainer" style="opacity: 0; pointer-events: none; display: none;">
                <span class="slider-label" id="sliderLabel">Slice Y</span>
                <input type="range" id="sliceSlider" min="0" max="100" value="50">
            </div>

            <div class="tab-bar" id="sliceTabs" style="display: none;">
                <button class="tab-btn" data-axis="Z" data-label="Top-Down Slice">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="2" x2="12" y2="22"></line>
                    </svg>
                    Top Down
                </button>

                <button class="tab-btn" data-axis="X" data-label="Side Slice">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 2a10 10 0 0 1 10 10c0 5.523-4.477 10-10 10S2 17.523 2 12 6.477 2 12 2Z"/>
                        <path d="M12 2v20"/>
                        <path d="M2 12h20"/>
                    </svg>
                    Side View
                </button>

                <button class="tab-btn active" data-axis="Y" data-label="Front-Back Slice">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                        <line x1="4" y1="12" x2="20" y2="12"/>
                    </svg>
                    Front-Back
                </button>
            </div>
        </div>

        <script>
            const iframe = document.getElementById('presentationFrame');
            const tabs = document.querySelectorAll('.tab-btn');
            const sliderCont = document.getElementById('sliderContainer');
            const slider = document.getElementById('sliceSlider');
            const sliderLabel = document.getElementById('sliderLabel');
            const loader = document.getElementById('loader');

            const viewToggles = document.querySelectorAll('.toggle-btn');
            const sliceTabsContainer = document.getElementById('sliceTabs');
            const toggleContainer = document.getElementById('viewToggle');

            let currentViewMode = 'surf'; // 'surf' or 'slice'
            let currentAxis = 'Y';
            let brainRef = null;
            let syncInterval = null;
            let currentDatasetHtml = 'none.html';

            // Handle View Type Switching (Surface vs Slice)
            viewToggles.forEach(btn => {
                btn.addEventListener('click', () => {
                    if(btn.classList.contains('active')) return;
                    viewToggles.forEach(t => t.classList.remove('active'));
                    btn.classList.add('active');
                    currentViewMode = btn.getAttribute('data-view');
                    updateIframeSource(currentDatasetHtml);
                });
            });

            function updateIframeSource(baseHtml) {
                if(!baseHtml || baseHtml === 'none.html') return;
                
                let targetSrc = baseHtml;
                // Currently only JBR supports dual views
                if (baseHtml === 'jbr_damage.html' && currentViewMode === 'slice') {
                    targetSrc = 'jbr_damage_slices.html';
                }

                iframe.src = targetSrc;
                
                if (currentViewMode === 'slice') {
                    sliceTabsContainer.style.display = 'flex';
                    sliderCont.style.display = 'flex';
                } else {
                    sliceTabsContainer.style.display = 'none';
                    sliderCont.style.display = 'none';
                }
            }

            // Handle Orientation Switching
            tabs.forEach(tab => {
                tab.addEventListener('click', () => {
                    if(tab.classList.contains('active')) return;
                    
                    tabs.forEach(t => t.classList.remove('active'));
                    tab.classList.add('active');

                    currentAxis = tab.getAttribute('data-axis');
                    sliderLabel.textContent = tab.getAttribute('data-label');
                    
                    if (iframe.contentWindow) {
                        iframe.contentWindow.postMessage({ axis: currentAxis }, "*");
                    }
                    if (brainRef && brainRef.nbSlice) {
                        setupSlider();
                    }
                });
            });

            // Re-initialize when iframe loads its content
            iframe.addEventListener('load', () => {
                const win = iframe.contentWindow;
                // Surface View and Slice View logic
                let attempts = 0;
                const pollTimer = setInterval(() => {
                    attempts++;
                    if (win && (win.window.brain || win.document.querySelector('canvas'))) {
                        clearInterval(pollTimer);
                        brainRef = win.window.brain;
                        loader.style.opacity = '0';
                        document.getElementById('mainOverlay').style.opacity = '1';
                        document.getElementById('mainOverlay').style.pointerEvents = 'auto';
                        
                        // Only show slice controls if we are in slice mode AND it's a brain file
                        const isBrainFile = currentDatasetHtml.includes('jbr_') || currentDatasetHtml.includes('perirhinal') || currentDatasetHtml.includes('white_matter');
                        
                        // Force slice mode for Perirhinal and WM for now (they don't have surface yet)
                        const supportsSurface = currentDatasetHtml === 'jbr_damage.html' || currentDatasetHtml === 'jbr_damage_slices.html';
                        toggleContainer.style.display = supportsSurface ? 'flex' : 'none';

                        if (currentViewMode === 'slice' || !supportsSurface) {
                            sliceTabsContainer.style.display = 'flex';
                            win.postMessage({ axis: currentAxis }, "*");
                            setupSlider();
                        } else {
                            sliceTabsContainer.style.display = 'none';
                            sliderCont.style.display = 'none';
                        }
                    } else if (attempts > 30) {
                        clearInterval(pollTimer);
                        loader.style.opacity = '0';
                        // Keep overlay for toggles if applicable, otherwise hide
                        document.getElementById('mainOverlay').style.opacity = '0';
                        document.getElementById('mainOverlay').style.pointerEvents = 'none';
                    }
                }, 100);
            });

            function setupSlider() {
                if(!brainRef || !brainRef.nbSlice) {
                    sliderCont.style.display = 'none';
                    return;
                }

                const maxSlice = brainRef.nbSlice[currentAxis] - 1;
                slider.min = 0;
                slider.max = maxSlice;
                slider.value = brainRef.numSlice[currentAxis];
                
                // Show slider smoothly
                sliderCont.style.display = 'flex';
                sliderCont.style.opacity = '1';
                sliderCont.style.pointerEvents = 'auto';

                // Sync slider if user clicks on the 3D canvas
                if (syncInterval) clearInterval(syncInterval);
                syncInterval = setInterval(() => {
                    if (brainRef && sliderCont.style.opacity === '1' && currentViewMode === 'slice') {
                        const currentModelVal = brainRef.numSlice[currentAxis];
                        if (parseInt(slider.value, 10) !== currentModelVal) {
                            slider.value = currentModelVal;
                        }
                    }
                }, 100);
            }

            // Handle Drag Scrubbing
            slider.addEventListener('input', (e) => {
                if (brainRef) {
                    const val = parseInt(e.target.value, 10);
                    brainRef.numSlice[currentAxis] = val;
                    brainRef.drawAll();
                }
            });

            function pollAdminState() {
                fetch('state.php', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'ping', username: <?= json_encode($username) ?> })
                })
                .then(r => r.json())
                .then(data => {
                    if (data.status === 'kicked') window.location.href = 'index.php?kicked=1';
                    
                    if (data.current_view && data.current_view !== currentDatasetHtml) {
                        const oldHtml = currentDatasetHtml;
                        currentDatasetHtml = data.current_view;
                        loader.style.opacity = '1';
                        // Reset to Surface mode for a new transition if it's jbr
                        if (currentDatasetHtml === 'jbr_damage.html') {
                            // currentViewMode = 'surf'; // Optionally keep user preference
                        }
                        updateIframeSource(currentDatasetHtml);
                        brainRef = null;
                    }
                }).catch(err => console.error("Poll error:", err));
            }
            pollAdminState(); // Fire immediately
            setInterval(pollAdminState, 2000);

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
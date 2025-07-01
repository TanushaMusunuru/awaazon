<?php

define('SESSION_DIR', _DIR_ . '/sessions/');
define('CODE_EXPIRY_SECONDS', 180);
define('MAX_ATTEMPTS', 3);

define('USE_EXOTEL', true);

define('EXOTEL_SID', 'your_SID_here');
define('EXOTEL_TOKEN', 'your_exotel_token');
define('EXOTEL_VIRTUAL_NUMBER', 'your_virtual_number');
define('EXOTEL_FLOW_ID', 'your_exotel_flow_id');

// ========== SETUP ==========
if (!file_exists(SESSION_DIR)) mkdir(SESSION_DIR, 0777, true);

// ========== USSD REQUEST ==========
$sessionId   = $_POST["sessionId"] ?? '';
$serviceCode = $_POST["serviceCode"] ?? '';
$phoneNumber = $_POST["phoneNumber"] ?? 'your_number';
$text        = strtoupper(trim($_POST["text"] ?? ''));

file_put_contents("debug_log.txt", "[" . date("Y-m-d H:i:s") . "] Phone received: $phoneNumber\n", FILE_APPEND);


$cleanPhone = preg_replace('/[^0-9]/', '', $phoneNumber);
if (substr($cleanPhone, 0, 2) !== '91' && strlen($cleanPhone) == 10) {
    $cleanPhone = '91' . $cleanPhone;
}

$sessionFile = SESSION_DIR . md5($cleanPhone) . ".json";

if (!file_exists($sessionFile)) {
    $session = [
        'code' => '2605',
        'timestamp' => time(),
        'used' => false,
        'attempts' => 0,
        'cartValue' => 400,
        'isNewUser' => false,
        'locationMismatch' => false
    ];
    file_put_contents($sessionFile, json_encode($session));
}


function loadSession($file) {
    if (!file_exists($file)) return null;
    return json_decode(file_get_contents($file), true);
}

function saveSession($file, $data) {
    file_put_contents($file, json_encode($data));
}

function isExpired($timestamp) {
    return (time() - $timestamp > CODE_EXPIRY_SECONDS);
}

function calculateRisk($session) {
    $risk = 0;
    if ($session['cartValue'] > 500) $risk += 30;
    if ($session['attempts'] > 2) $risk += 20;
    $hour = (int)date('H');
    if ($hour >= 22 || $hour < 6) $risk += 15;
    if ($session['isNewUser']) $risk += 20;
    if ($session['locationMismatch']) $risk += 15;
    return $risk;
}

function triggerIVRCall($to) {
    if (!USE_EXOTEL) {
        file_put_contents("ivr_test_log.txt", "[" . date("Y-m-d H:i:s") . "] Simulated IVR call to: $to\n", FILE_APPEND);
        return true;
    }

    $url = "https://" . EXOTEL_SID . ":" . EXOTEL_TOKEN . "@api.exotel.com/v1/Accounts/" . EXOTEL_SID . "/Calls/connect";

    $post_data = [
        'From' => $to,
        'To' => EXOTEL_VIRTUAL_NUMBER,
        'CallerId' => EXOTEL_VIRTUAL_NUMBER,
        'CallType' => 'trans',
        'Url' => "https://my.exotel.in/ivr/static/" . EXOTEL_FLOW_ID . ".xml"
    ];

    $ch = curl_init();
    curl_setopt($ch, CURLOPT_VERBOSE, 1);
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_POST, 1);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
    curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query($post_data));
    $response = curl_exec($ch);
    curl_close($ch);

    file_put_contents("ivr_test_log.txt", "[" . date("Y-m-d H:i:s") . "] Exotel Response: $response\n", FILE_APPEND);
    return $response;
}

$session = loadSession($sessionFile);
$response = "";

header("Content-Type: text/plain");

if ($text === "") {
    $response = "CON Enter 4-character code shown on screen to confirm your order:";
} else {
    if (!$session) {
        $response = "END ⚠ No session found. Please request a new code.";
    }
    elseif ($session['used']) {
        $response = "END ❌ Code already used.";
    }
    elseif (isExpired($session['timestamp'])) {
        $session['used'] = true;
        saveSession($sessionFile, $session);
        $response = "END ⏱ Code expired. Please get a new one.";
    }
    elseif ($session['attempts'] >= MAX_ATTEMPTS) {
        $response = "END 🔒 Too many wrong attempts.";
    }
    elseif ($text === strtoupper($session['code'])) {
        $risk = calculateRisk($session);
        $session['used'] = true;
        saveSession($sessionFile, $session);

        if ($risk < 50) {
            triggerIVRCall($cleanPhone);
            $response = "✅ Verified! You'll be redirected to call shortly.";
        } else {
            $response = "END ⚠ High Risk ($risk%). Request forwarded to SHG for manual approval.";
        }
    } else {
        $session['attempts'] += 1;
        saveSession($sessionFile, $session);
        $response = "END ❌ Wrong code. Attempt {$session['attempts']} of " . MAX_ATTEMPTS . ".";
    }
}

echo $response;
?>
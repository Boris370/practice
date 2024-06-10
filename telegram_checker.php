<?php
// Подключение к базе данных PostgreSQL
$host = 'localhost';
$dbname = 'for_tg_bot';
$user = 'postgres';
$password = 'plut2011';
$dsn = "pgsql:host=$host;dbname=$dbname";

try {
    $pdo = new PDO($dsn, $user, $password);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch (PDOException $e) {
    die("Ошибка подключения к базе данных: " . $e->getMessage());
}

// Проверка наличия токена в GET-параметрах
if (!isset($_GET['t'])) {
    die("Токен не предоставлен.");
}

$token = $_GET['t'];

// Получение логина Telegram по токену
$stmt = $pdo->prepare("SELECT telegram_login FROM users_to_telegram WHERE token = :token");
$stmt->execute(['token' => $token]);
$telegram_login = $stmt->fetchColumn();

if (!$telegram_login) {
    die("Неверный токен.");
}

// Если форма авторизации отправлена
if ($_SERVER['REQUEST_METHOD'] == 'POST') {
    $username = $_POST['username'];

    // Проверка логина
    if ($username == $telegram_login) {
        // Генерация user_id (в реальной ситуации, нужно использовать настоящий идентификатор пользователя)
        $user_id = random_int(1000, 9999);

        // Обновление записи в базе данных
        $stmt = $pdo->prepare("UPDATE users_to_telegram SET user_id = :user_id WHERE token = :token");
        $stmt->execute(['user_id' => $user_id, 'token' => $token]);

        echo "Авторизация прошла успешно. Вы можете вернуться в Telegram.";
        exit;
    } else {
        echo "Неверный логин.";
    }
}
?>

<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Авторизация</title>
</head>
<body>
    <h1>Авторизация</h1>
    <form method="post">
        <label for="username">Логин:</label>
        <input type="text" id="username" name="username" required>
        <br>
        <button type="submit">Войти</button>
    </form>
</body>
</html>

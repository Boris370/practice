<?php
$directory = 'uploads/';
$files = scandir($directory);
?>
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Загруженные файлы</title>
</head>
<body>
    <h1>Загруженные файлы</h1>
    <ul>
        <?php foreach ($files as $file): ?>
            <?php if ($file !== '.' && $file !== '..'): ?>
                <li><a href="<?php echo $directory . $file; ?>" target="_blank"><?php echo $file; ?></a></li>
            <?php endif; ?>
        <?php endforeach; ?>
    </ul>
</body>
</html>

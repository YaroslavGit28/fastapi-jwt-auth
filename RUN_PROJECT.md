## Как запустить проект локально (для отчёта)

1) Установить зависимости:
- `pip install -r requirements.txt`

2) Запустить сервер:
- `uvicorn main:app --reload --port 8000`

3) Проверить, что сервис отвечает:
- `GET /health`

4) Пример логина для получения JWT:
- `POST /auth/login`
- body (JSON):
  - `{"username": "admin", "password": "admin123"}`
  - или `{"username": "user", "password": "user123"}`

5) Использовать access token для защищённого роутера:
- `GET /users/me`
- заголовок `Authorization: Bearer <access_token>`

Ожидаемые ответы:
- при успешном логине: `200` и JSON с `access_token`
- при валидном токене: `200` и `UserResponse`
- при ошибках подписи/истечения срока: `401`


import logging
import requests

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    try:
        # Получаем список ожидающих пользователей
        response = requests.get('http://localhost:8000/matchmaking/users?test_name=test_0&epoch=00000000-0000-0000-0000-000000000000')
        logger.info(f"GET /matchmaking/users response: {response.status_code} {response.text}")
        
        if response.status_code == 200:
            users_data = response.json()
            
            # Отправляем запрос на создание матча
            headers = {'Content-Type': 'application/json'}
            create_match_response = requests.post(
                'http://localhost:8000/matchmaking/create_match',
                headers=headers,
                json={"test_name": "test_0", "epoch": "00000000-0000-0000-0000-000000000000", "users": users_data['user']}
            )
            logger.info(f"POST /matchmaking/create_match response: {create_match_response.status_code} {create_match_response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")

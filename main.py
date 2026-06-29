
import logging,requests,os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

# Налаштування логування
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Конфігурація підключень
DB_CONFIG = {
    'host': os.getenv('HOST','localhost') ,
    'user': os.getenv('USER','user'),
    'password': os.getenv('PASSWORD'),
    'database': os.getenv('DATABASE'),
    'port': int(os.getenv('PORT')),
    'collation': 'utf8mb4_general_ci'
}

EZ_API_TOKEN = os.getenv('EZ_API_TOKEN')
EZ_API_URL   = os.getenv('EZ_API_URL')

EZ_HEADERS = {
    "Authorization": f"Bearer {EZ_API_TOKEN}",
    "Content-Type": "application/json",
    "X-Timezone-Name": "Europe/Kyiv",
    "X-Timezone-Offset": "180"
}

def get_transactions():
    conn   = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    query  = """ select id,export_json 
                from v_export_json vej 
                where vej.processed_at is null             
            """
    try:
        cursor.execute(query)
        raw_data =  cursor.fetchall()
        return raw_data
    except mysql.connector.Error as err:
        logging.error(f"Помилка читання бази даних: {err}")
        return []
    finally:
        cursor.close()
        conn.close()

def update_transactions(id,debug = 0):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    try:
        if debug == 0:
            cursor.callproc('mark_processed', [id])
        logging.info(f"Оновлено webhook {id}")
        conn.commit()
    except mysql.connector.Error as err:
        logging.error(f"Помилка оновлення запису {id} : {err}")
    finally:
        cursor.close()
        conn.close()

def post_transactions():
    data = get_transactions()
    if not data:
        logging.info(f"Відсутні нові транзакції")
    else:
        for payload in data:
            try:
                raw_json_string = payload['export_json']
                id = payload['id']
                # Робимо авторизований PUT/POST запит до ezBookkeeping
                response = requests.post(
                    EZ_API_URL,
                    data=raw_json_string.encode('utf-8'),
                    headers=EZ_HEADERS,
                    timeout=5)

                if response.status_code in [200, 204]:
                    logging.info(f"Імпортовано транзакцію {id}")
                    update_transactions(id, 0)
                elif response.status_code in [401, 403]:
                    logging.error("Помилка авторизації в ezBookkeeping! Перевірте правильність токена.")
                else:
                    logging.warning(
                        f"Невдале імпортування ID {id}. Статус: {response.status_code}, Відповідь: {response.text}")
            except requests.RequestException as e:
                logging.error(f"Помилка мережі при запиті до ez-API: {e}")

def post_test():
    data = get_transactions()
    for payload in data:
        try:
            raw_json_string = payload['export_json']
            id = payload['id']
            print(id,raw_json_string)
            update_transactions(id,1)
        except requests.RequestException as e:
            logging.error(f"Помилка мережі при запиті до ez-API: {e}")

if __name__ == "__main__":
    post_transactions()
    # get_transactions()
    # post_test()


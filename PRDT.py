import asyncio
import json
import random
import requests
import traceback
from eth_account import Account
from eth_account.messages import encode_defunct
from colorama import Fore, Style
from datetime import datetime, timezone, timedelta
import cloudscraper
import time

# Инициализация colorama
from colorama import init
init()

# Функция для загрузки данных из файлов
def load_file(filename: str) -> list[str]:
    try:
        with open(filename, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"{Fore.RED}✗ Файл {filename} не найден{Style.RESET_ALL}", flush=True)
        return []
    except Exception as e:
        print(f"{Fore.RED}✗ Ошибка чтения файла {filename}: {e}{Style.RESET_ALL}", flush=True)
        return []

# Функция для загрузки user-agent'ов
def load_ua() -> dict:
    try:
        with open('ua.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"{Fore.YELLOW}✓ Файл ua.json не найден, создаем новый{Style.RESET_ALL}", flush=True)
        return {}
    except json.JSONDecodeError as e:
        print(f"{Fore.RED}✗ Ошибка загрузки ua.json: {e}. Создаем новый файл{Style.RESET_ALL}", flush=True)
        with open('ua.json', 'w') as f:
            json.dump({}, f, indent=4)
        return {}
    except Exception as e:
        print(f"{Fore.RED}✗ Ошибка загрузки ua.json: {e}{Style.RESET_ALL}", flush=True)
        return {}

# Функция для сохранения user-agent'а
def save_ua(address: str, ua_data: dict, ua_dict: dict) -> None:
    try:
        ua_dict[address] = ua_data
        with open('ua.json', 'w') as f:
            json.dump(ua_dict, f, indent=4)
        print(f"{Fore.GREEN}✓ User-agent для {address} сохранен{Style.RESET_ALL}", flush=True)
    except Exception as e:
        print(f"{Fore.RED}✗ Ошибка сохранения ua.json: {e}{Style.RESET_ALL}", flush=True)

# Функция для загрузки времён чек-инов
def load_next_checkins() -> dict:
    try:
        with open('next_checkins.json', 'r') as f:
            next_checkins = json.load(f)
        # Очищаем записи, у которых время чек-ина слишком далеко в прошлом
        current_timestamp = datetime.now(timezone.utc).timestamp()
        cleaned_checkins = {
            address: time for address, time in next_checkins.items()
            if iso_to_timestamp(time) > current_timestamp - 86400  
        }
        if len(cleaned_checkins) != len(next_checkins):
            with open('next_checkins.json', 'w') as f:
                json.dump(cleaned_checkins, f, indent=4)
            print(f"{Fore.YELLOW}✓ Очищены устаревшие записи в next_checkins.json{Style.RESET_ALL}", flush=True)
        return cleaned_checkins
    except FileNotFoundError:
        print(f"{Fore.YELLOW}✓ Файл next_checkins.json не найден, создаем новый{Style.RESET_ALL}", flush=True)
        return {}
    except json.JSONDecodeError as e:
        print(f"{Fore.RED}✗ Ошибка загрузки next_checkins.json: {e}. Создаем новый файл{Style.RESET_ALL}", flush=True)
        with open('next_checkins.json', 'w') as f:
            json.dump({}, f, indent=4)
        return {}
    except Exception as e:
        print(f"{Fore.RED}✗ Ошибка загрузки next_checkins.json: {e}{Style.RESET_ALL}", flush=True)
        return {}

# Функция для сохранения времени следующего чек-ина
def save_next_checkin(address: str, next_check_in_time: str, next_checkins: dict) -> None:
    try:
        # Проверка формата времени
        datetime.fromisoformat(next_check_in_time.replace("Z", "+00:00"))
        next_checkins[address] = next_check_in_time
        with open('next_checkins.json', 'w') as f:
            json.dump(next_checkins, f, indent=4)
        print(f"{Fore.GREEN}✓ Время следующего чек-ина для {address} сохранено{Style.RESET_ALL}", flush=True)
    except ValueError as e:
        print(f"{Fore.RED}✗ Некорректный формат времени {next_check_in_time}: {e}{Style.RESET_ALL}", flush=True)
    except Exception as e:
        print(f"{Fore.RED}✗ Ошибка сохранения next_checkins.json: {e}{Style.RESET_ALL}", flush=True)

# Функция проверки прокси
def check_proxy(proxy: str, proxies: list, timeout: int = 30) -> str | None:
    max_attempts = 5
    current_proxy = proxy
    tried_proxies = set()

    while current_proxy and len(tried_proxies) < len(proxies):
        tried_proxies.add(current_proxy)
        proxy_clean = current_proxy.replace("http://", "")
        proxy_dict = {"http": f"http://{proxy_clean}", "https": f"http://{proxy_clean}"}
        test_url = "https://api.ipify.org?format=json"

        for attempt in range(1, max_attempts + 1):
            print(f"Проверка прокси {proxy_clean} (попытка {attempt}/{max_attempts})", flush=True)
            try:
                response = requests.get(test_url, proxies=proxy_dict, timeout=timeout)
                if response.status_code == 200:
                    print(f"{Fore.GREEN}✓ Прокси {proxy_clean} работает{Style.RESET_ALL}", flush=True)
                    return current_proxy
                else:
                    print(f"{Fore.RED}✗ Прокси {proxy_clean} не работает: HTTP {response.status_code}{Style.RESET_ALL}", flush=True)
                    if attempt < max_attempts:
                        time.sleep(random.uniform(5, 10))
            except Exception as e:
                print(f"{Fore.RED}✗ Прокси {proxy_clean} не работает: {e}{Style.RESET_ALL}", flush=True)
                if attempt < max_attempts:
                    time.sleep(random.uniform(5, 10))

        remaining_proxies = [p for p in proxies if p not in tried_proxies]
        current_proxy = random.choice(remaining_proxies) if remaining_proxies else None
        if current_proxy:
            print(f"{Fore.YELLOW}✓ Прокси {proxy_clean} не сработал, пробую другой: {current_proxy}{Style.RESET_ALL}", flush=True)

    print(f"{Fore.YELLOW}✓ Все прокси не работают, пробуем без прокси{Style.RESET_ALL}", flush=True)
    return None

# Функция для получения сообщения для подписи
def get_auth_message(account_index: int, address: str, proxy: str, user_agent_data: dict) -> dict | None:
    proxy_clean = proxy.replace("http://", "") if proxy else None
    proxy_dict = {"http": f"http://{proxy_clean}", "https": f"http://{proxy_clean}"} if proxy else {}
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "identity",
        "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7,kk;q=0.6",
        "content-type": "application/json",
        "origin": "https://prdt.finance",
        "priority": "u=1, i",
        "referer": "https://prdt.finance/",
        "sec-ch-ua": user_agent_data["sec-ch-ua"],
        "sec-ch-ua-mobile": user_agent_data["sec-ch-ua-mobile"],
        "sec-ch-ua-platform": user_agent_data["sec-ch-ua-platform"],
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": user_agent_data["user_agent"],
    }
    payload = {
        "address": address.lower(),
        "chain": 137,
        "network": "evm"
    }
    url = "https://api7.prdt.finance/auth/request-message"
    max_attempts = 5
    scraper = cloudscraper.create_scraper()

    for attempt in range(1, max_attempts + 1):
        print(f"[{account_index}] Получение сообщения для подписи (попытка {attempt}/{max_attempts})", flush=True)
        try:
            response = scraper.post(url, headers=headers, json=payload, proxies=proxy_dict, timeout=60)
            print(f"[{account_index}] HTTP-код ответа: {response.status_code}", flush=True)
            print(f"[{account_index}] Заголовки ответа: {response.headers}", flush=True)
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"[{account_index}] Ответ сервера: {data}", flush=True)
                    return {"data": data, "cookies": response.cookies.get_dict()}
                except ValueError:
                    print(f"{Fore.RED}[{account_index}] ✗ Ошибка парсинга JSON: {response.text}{Style.RESET_ALL}", flush=True)
            else:
                print(f"{Fore.RED}[{account_index}] ✗ Ошибка получения сообщения: HTTP {response.status_code}, {response.text}{Style.RESET_ALL}", flush=True)

            if attempt == max_attempts - 1:
                print(f"[{account_index}] Пробуем без прокси...", flush=True)
                response = scraper.post(url, headers=headers, json=payload, timeout=60)
                print(f"[{account_index}] HTTP-код ответа (без прокси): {response.status_code}", flush=True)
                print(f"[{account_index}] Заголовки ответа (без прокси): {response.headers}", flush=True)
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"[{account_index}] Ответ сервера (без прокси): {data}", flush=True)
                        return {"data": data, "cookies": response.cookies.get_dict()}
                    except ValueError:
                        print(f"{Fore.RED}[{account_index}] ✗ Ошибка парсинга JSON (без прокси): {response.text}{Style.RESET_ALL}", flush=True)
                else:
                    print(f"{Fore.RED}[{account_index}] ✗ Ошибка без прокси: HTTP {response.status_code}, {response.text}{Style.RESET_ALL}", flush=True)

            if attempt < max_attempts:
                time.sleep(random.uniform(5, 10))
        except Exception as e:
            print(f"{Fore.RED}[{account_index}] ✗ Ошибка получения сообщения: {e}\n{traceback.format_exc()}{Style.RESET_ALL}", flush=True)
            if attempt < max_attempts:
                time.sleep(random.uniform(5, 10))
    return None

# Функция для подписи сообщения
def sign_message(account_index: int, private_key: str, address: str, message: str) -> str | None:
    try:
        account = Account.from_key(private_key)
        if account.address.lower() != address.lower():
            print(f"{Fore.RED}[{account_index}] ✗ Приватный ключ не соответствует адресу {address}{Style.RESET_ALL}", flush=True)
            return None
        signable_message = encode_defunct(text=message)
        signed_message = Account.sign_message(signable_message, private_key=private_key)
        signature = signed_message.signature.hex()
        print(f"[{account_index}] Подпись сообщения: {signature}", flush=True)
        return signature
    except Exception as e:
        print(f"{Fore.RED}[{account_index}] ✗ Ошибка создания подписи: {e}\n{traceback.format_exc()}{Style.RESET_ALL}", flush=True)
        return None

# Функция авторизации
def login(account_index: int, address: str, private_key: str, proxy: str, user_agent_data: dict) -> dict | None:
    proxy_clean = proxy.replace("http://", "") if proxy else None
    proxy_dict = {"http": f"http://{proxy_clean}", "https": f"http://{proxy_clean}"} if proxy else {}
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "identity",
        "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7,kk;q=0.6",
        "content-type": "application/json",
        "origin": "https://prdt.finance",
        "priority": "u=1, i",
        "referer": "https://prdt.finance/",
        "sec-ch-ua": user_agent_data["sec-ch-ua"],
        "sec-ch-ua-mobile": user_agent_data["sec-ch-ua-mobile"],
        "sec-ch-ua-platform": user_agent_data["sec-ch-ua-platform"],
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": user_agent_data["user_agent"],
    }

    auth_response = get_auth_message(account_index, address, proxy, user_agent_data)
    if not auth_response:
        print(f"{Fore.RED}[{account_index}] ✗ Не удалось получить сообщение для подписи{Style.RESET_ALL}", flush=True)
        return None

    auth_data = auth_response["data"]
    cookies = auth_response["cookies"]
    message = auth_data.get("message")
    nonce = auth_data.get("nonce")

    signature = sign_message(account_index, private_key, address, message)
    if not signature:
        return None

    cookie_string = "; ".join([f"{key}={value}" for key, value in cookies.items()])
    if cookie_string:
        headers["cookie"] = cookie_string

    payload = {
        "address": address.lower(),
        "message": message,
        "nonce": nonce,
        "signature": f"0x{signature}",
        "ip": "37.151.35.213"
    }
    print(f"[{account_index}] Отправляемый payload: {payload}", flush=True)
    url = "https://api7.prdt.finance/auth/verify"
    max_attempts = 5
    scraper = cloudscraper.create_scraper()

    for attempt in range(1, max_attempts + 1):
        print(f"[{account_index}] Попытка авторизации для {address} (попытка {attempt}/{max_attempts})", flush=True)
        try:
            response = scraper.post(url, headers=headers, json=payload, proxies=proxy_dict, timeout=60)
            print(f"[{account_index}] HTTP-код ответа: {response.status_code}", flush=True)
            print(f"[{account_index}] Заголовки ответа: {response.headers}", flush=True)
            print(f"[{account_index}] Ответ сервера: {response.text}", flush=True)
            if response.status_code == 200:
                cookies = response.cookies.get_dict()
                access_token = cookies.get("accessToken")
                refresh_token = cookies.get("refreshToken")
                if access_token and refresh_token:
                    print(f"{Fore.GREEN}[{account_index}] ✓ Успешная авторизация для {address}{Style.RESET_ALL}", flush=True)
                    return {"access_token": access_token, "refresh_token": refresh_token}
                else:
                    print(f"{Fore.RED}[{account_index}] ✗ Токены не найдены в ответе{Style.RESET_ALL}", flush=True)
                    return None
            else:
                print(f"{Fore.RED}[{account_index}] ✗ Ошибка авторизации: HTTP {response.status_code}, {response.text}{Style.RESET_ALL}", flush=True)
            if attempt < max_attempts:
                time.sleep(random.uniform(5, 10))
        except Exception as e:
            print(f"{Fore.RED}[{account_index}] ✗ Ошибка авторизации: {e}\n{traceback.format_exc()}{Style.RESET_ALL}", flush=True)
            if attempt < max_attempts:
                time.sleep(random.uniform(5, 10))
    return None

# Функция для выполнения чек-ина
def check_in(account_index: int, address: str, access_token: str, refresh_token: str, proxy: str, user_agent_data: dict) -> dict | None:
    proxy_clean = proxy.replace("http://", "") if proxy else None
    proxy_dict = {"http": f"http://{proxy_clean}", "https": f"http://{proxy_clean}"} if proxy else {}
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "identity",
        "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7,kk;q=0.6",
        "content-type": "application/json",
        "origin": "https://prdt.finance",
        "priority": "u=1, i",
        "referer": "https://prdt.finance/",
        "sec-ch-ua": user_agent_data["sec-ch-ua"],
        "sec-ch-ua-mobile": user_agent_data["sec-ch-ua-mobile"],
        "sec-ch-ua-platform": user_agent_data["sec-ch-ua-platform"],
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": user_agent_data["user_agent"],
        "cookie": f"accessToken={access_token}; refreshToken={refresh_token}"
    }
    payload = {}
    url = "https://apim.prdt.finance/api/v1/mine/checkin"
    max_attempts = 3
    scraper = cloudscraper.create_scraper()

    for attempt in range(1, max_attempts + 1):
        print(f"[{account_index}] Попытка чек-ина для {address} (попытка {attempt}/{max_attempts})", flush=True)
        try:
            response = scraper.post(url, headers=headers, json=payload, proxies=proxy_dict, timeout=60)
            print(f"[{account_index}] HTTP-код ответа: {response.status_code}", flush=True)
            print(f"[{account_index}] Заголовки ответа: {response.headers}", flush=True)
            try:
                data = response.json()
                print(f"[{account_index}] Ответ сервера: {data}", flush=True)
                if response.status_code == 200 and data.get("success"):
                    print(f"{Fore.GREEN}[{account_index}] ✓ Чек-ин успешно выполнен для {address}. Следующий чек-ин: {data['user']['nextCheckInActive']}{Style.RESET_ALL}", flush=True)
                    return {
                        "success": True,
                        "nextCheckInActive": data["user"].get("nextCheckInActive"),
                        "minedTokens": data["user"].get("minedTokens")
                    }
                elif response.status_code == 400 and data.get("message") == "Check-in not within valid window":
                    print(f"{Fore.YELLOW}[{account_index}] Чек-ин уже выполнен для {address}{Style.RESET_ALL}", flush=True)
                    return {"success": False, "already_checked_in": True}
                elif response.status_code == 401:
                    print(f"{Fore.RED}[{account_index}] ✗ Токен недействителен: {data.get('msg', 'Нет сообщения')}{Style.RESET_ALL}", flush=True)
                    return {"success": False, "reauth_required": True}
                else:
                    print(f"{Fore.RED}[{account_index}] ✗ Ошибка чек-ина: {data.get('msg', data.get('message', 'Нет сообщения'))}, HTTP {response.status_code}{Style.RESET_ALL}", flush=True)
                    return {"success": False, "reauth_required": False}
            except ValueError:
                print(f"{Fore.RED}[{account_index}] ✗ Ошибка парсинга JSON: {response.text}{Style.RESET_ALL}", flush=True)
            if attempt < max_attempts:
                time.sleep(random.uniform(5, 10))
        except Exception as e:
            print(f"{Fore.RED}[{account_index}] ✗ Ошибка чек-ина: {e}\n{traceback.format_exc()}{Style.RESET_ALL}", flush=True)
            if attempt < max_attempts:
                time.sleep(random.uniform(5, 10))
    return {"success": False, "reauth_required": False}

# Функция для преобразования времени ISO в timestamp
def iso_to_timestamp(iso_time: str) -> float:
    try:
        dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        return dt.timestamp()
    except Exception as e:
        print(f"{Fore.RED}✗ Ошибка преобразования времени {iso_time}: {e}{Style.RESET_ALL}", flush=True)
        return 0  

# Функция обработки одного аккаунта
async def process_account(index: int, private_key: str, proxies: list, user_agents_data: list, stats: dict, ua_dict: dict, next_checkins: dict) -> None:
    print(f"[{index}] Начало обработки аккаунта", flush=True)
    stats["total_accounts"] += 1

    proxy = random.choice(proxies) if proxies else None
    if not proxy:
        print(f"{Fore.RED}[{index}] ✗ Нет доступных прокси, пробуем без прокси{Style.RESET_ALL}", flush=True)

    print(f"[{index}] Проверка прокси...", flush=True)
    proxy = check_proxy(proxy, proxies) if proxy else None

    print(f"[{index}] Получение адреса...", flush=True)
    try:
        account = Account.from_key(private_key)
        address = account.address
    except Exception as e:
        print(f"{Fore.RED}[{index}] ✗ Ошибка с приватным ключом: {e}\n{traceback.format_exc()}{Style.RESET_ALL}", flush=True)
        stats["login_errors"] += 1
        return

    print(f"[{index}] Обрабатываю аккаунт {address} с прокси {proxy or 'без прокси'}", flush=True)

    print(f"[{index}] Проверка user-agent...", flush=True)
    ua_data = ua_dict.get(address)
    if not ua_data:
        ua_data = random.choice(user_agents_data)
        save_ua(address, ua_data, ua_dict)
    print(f"[{index}] Использую user-agent: {ua_data['user_agent']}", flush=True)

    next_check_in_time = next_checkins.get(address)
    current_timestamp = datetime.now(timezone.utc).timestamp()
    if next_check_in_time:
        next_check_in_timestamp = iso_to_timestamp(next_check_in_time)
        print(f"[{index}] Текущее время: {datetime.fromtimestamp(current_timestamp, timezone.utc).isoformat()}, следующее время чек-ина: {next_check_in_time} ({next_check_in_timestamp})", flush=True)
        if current_timestamp < next_check_in_timestamp:
            print(f"[{index}] Чек-ин для {address} уже выполнен, следующий запланирован на {next_check_in_time}", flush=True)
            stats["successful_checkins"] += 1
            return

    print(f"[{index}] Выполняю авторизацию для чек-ина...", flush=True)
    try:
        token_data = login(index, address, private_key, proxy, ua_data)
        if not token_data:
            print(f"{Fore.RED}[{index}] ✗ Не удалось авторизоваться{Style.RESET_ALL}", flush=True)
            stats["login_errors"] += 1
            return

        stats["successful_logins"] += 1
        result = check_in(index, address, token_data["access_token"], token_data["refresh_token"], proxy, ua_data)
        if result and result.get("success"):
            stats["successful_checkins"] += 1
            next_check_in_time = result["nextCheckInActive"]
            save_next_checkin(address, next_check_in_time, next_checkins)
            print(f"[{index}] Следующий чек-ин запланирован на {next_check_in_time}", flush=True)
        elif result and result.get("already_checked_in"):
            stats["successful_checkins"] += 1
            other_checkins = [iso_to_timestamp(t) for t in next_checkins.values() if t]
            if other_checkins:
                avg_checkin_time = sum(other_checkins) / len(other_checkins)
                next_check_in_time = (datetime.fromtimestamp(avg_checkin_time, timezone.utc) + timedelta(hours=24)).isoformat().replace("+00:00", "Z")
            else:
                next_check_in_time = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat().replace("+00:00", "Z")
            save_next_checkin(address, next_check_in_time, next_checkins)
            print(f"[{index}] Чек-ин уже выполнен, следующий запланирован на {next_check_in_time} (оценка)", flush=True)
        elif result and result.get("reauth_required"):
            print(f"{Fore.RED}[{index}] ✗ Токен недействителен, нужна повторная авторизация{Style.RESET_ALL}", flush=True)
            stats["login_errors"] += 1
        else:
            stats["checkin_errors"] += 1
            print(f"{Fore.RED}[{index}] ✗ Не удалось выполнить чек-ин{Style.RESET_ALL}", flush=True)

    except Exception as e:
        print(f"{Fore.RED}[{index}] ✗ Ошибка обработки аккаунта: {e}\n{traceback.format_exc()}{Style.RESET_ALL}", flush=True)
        stats["checkin_errors"] += 1

# Функция для записи статистики
async def save_stats(stats: dict) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stats_text = (
        f"PRDT.Finance Auth Script Statistics\n"
        f"Дата: {timestamp}\n"
        f"Всего аккаунтов обработано: {stats['total_accounts']}\n"
        f"Успешных авторизаций: {stats['successful_logins']}\n"
        f"Успешных чек-инов: {stats.get('successful_checkins', 0)}\n"
        f"Ошибок авторизации: {stats['login_errors']}\n"
        f"Ошибок чек-ина: {stats.get('checkin_errors', 0)}\n"
    )
    try:
        with open('prdt_stats.txt', 'w') as f:
            f.write(stats_text)
        print(f"{Fore.GREEN}✓ Статистика сохранена в prdt_stats.txt{Style.RESET_ALL}", flush=True)
    except Exception as e:
        print(f"{Fore.RED}✗ Ошибка сохранения статистики: {e}{Style.RESET_ALL}", flush=True)

# Основная функция
async def main() -> None:
    print(f"Загрузка файлов...", flush=True)
    accounts = load_file('accounts.txt')
    proxies = load_file('proxies.txt')

    try:
        with open('user_agents.json', 'r') as f:
            user_agents_data = json.load(f)["agents"]
    except FileNotFoundError:
        print(f"{Fore.RED}✗ Файл user_agents.json не найден{Style.RESET_ALL}", flush=True)
        return
    except json.JSONDecodeError:
        print(f"{Fore.RED}✗ Ошибка чтения user_agents.json: неверный JSON{Style.RESET_ALL}", flush=True)
        return
    except KeyError:
        print(f"{Fore.RED}✗ Ошибка: в user_agents.json отсутствует ключ 'agents'{Style.RESET_ALL}", flush=True)
        return

    if not accounts:
        print(f"{Fore.RED}✗ Не удалось загрузить аккаунты{Style.RESET_ALL}", flush=True)
        return

    print(f"Загрузка user-agent'ов...", flush=True)
    ua_dict = load_ua()

    print(f"Загрузка времён чек-инов...", flush=True)
    next_checkins = load_next_checkins()

    print(f"Найдено {len(accounts)} аккаунтов и {len(proxies)} прокси", flush=True)

    stats = {
        "total_accounts": 0,
        "successful_logins": 0,
        "successful_checkins": 0,
        "login_errors": 0,
        "checkin_errors": 0
    }

    print(f"Запуск в режиме демона...", flush=True)
    while True:
        current_timestamp = datetime.now(timezone.utc).timestamp()
        accounts_to_process = []
        next_checkin_timestamps = []

        for index, private_key in enumerate(accounts, 1):
            try:
                account = Account.from_key(private_key)
                address = account.address
                next_check_in_time = next_checkins.get(address)
                if not next_check_in_time:
                    print(f"[{index}] Нет времени чек-ина для {address}, добавляем в обработку", flush=True)
                    accounts_to_process.append((index, private_key))
                else:
                    next_check_in_timestamp = iso_to_timestamp(next_check_in_time)
                    print(f"[{index}] Время чек-ина для {address}: {next_check_in_time} ({next_check_in_timestamp}), текущее время: {current_timestamp}", flush=True)
                    if current_timestamp >= next_check_in_timestamp:
                        print(f"[{index}] Время чек-ина для {address} истекло, добавляем в обработку", flush=True)
                        accounts_to_process.append((index, private_key))
                    else:
                        print(f"[{index}] Чек-ин для {address} ещё не нужен", flush=True)
                    next_checkin_timestamps.append(next_check_in_timestamp)
            except Exception as e:
                print(f"{Fore.RED}✗ Ошибка с приватным ключом {index}: {e}{Style.RESET_ALL}", flush=True)
                stats["login_errors"] += 1

        if accounts_to_process:
            print(f"Обработка {len(accounts_to_process)} аккаунтов...", flush=True)
            for index, private_key in accounts_to_process:
                print(f"Запуск обработки аккаунта {index}...", flush=True)
                try:
                    await process_account(index, private_key, proxies, user_agents_data, stats, ua_dict, next_checkins)
                except Exception as e:
                    print(f"{Fore.RED}✗ Ошибка при обработке аккаунта {index}: {e}\n{traceback.format_exc()}{Style.RESET_ALL}", flush=True)
                    stats["checkin_errors"] += 1
                pause = random.uniform(10, 30)
                print(f"Пауза после аккаунта {index}: {pause:.2f} сек", flush=True)
                await asyncio.sleep(pause)
        else:
            if next_checkin_timestamps:
                min_next_checkin = min(next_checkin_timestamps)
                wait_time = max(0, min_next_checkin - current_timestamp)
                wait_time = min(wait_time, 600)  
                next_checkin_dt = datetime.fromtimestamp(min_next_checkin, timezone.utc)
                print(f"Нет аккаунтов для обработки, следующий чек-ин в {next_checkin_dt.isoformat()}, ожидание {wait_time:.2f} секунд", flush=True)
                await asyncio.sleep(wait_time)
            else:
                print(f"Нет сохранённых времён чек-инов, следующая проверка через 10 минут", flush=True)
                await asyncio.sleep(600)

        await save_stats(stats)

if __name__ == "__main__":
    asyncio.run(main())

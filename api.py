import requests
import requests

class Report_Generator:

    def __init__(self, api_key, start_date, end_date):
        """
        Inicializa la clase con los parámetros necesarios.

        Args:
            api_key (str): La clave de API para autenticar la solicitud.
            start_date (str): Fecha de inicio en formato YYYY-MM-DDTHH:MM:SS.
            end_date (str): Fecha de fin en formato YYYY-MM-DDTHH:MM:SS.
        """
        self.api_key = api_key
        self.start_date = start_date
        self.end_date = end_date

    @staticmethod
    def authenticate_to_backend():
        """
        Realiza la autenticación al backend y devuelve el JSON generado.

        Returns:
            str: El API key si la solicitud fue exitosa, None si no lo fue.
        """
        url = "http://127.0.0.1:3001/v1/login"
        data = {
            "username": "luisIntelcon",
            "password": "123456"
        }

        try:
            response = requests.post(url, json=data)

            if response.status_code == 200:
                print("Datos obtenidos exitosamente del backend.")
                json_response = response.json()
                api_key = json_response.get("apiKey")
                print(f"API Key obtenida: {api_key}")
                return api_key
            else:
                print(f"Error al hacer el llamado: {response.status_code}")
                print("Mensaje de error:", response.json())
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error en la solicitud al backend: {e}")
            return None

    def fetch_data_from_backend(self):
        """
        Realiza una solicitud al backend y retorna el JSON de respuesta.

        Returns:
            dict: El JSON de respuesta si la solicitud fue exitosa, None si no lo fue.
        """
        url = "http://127.0.0.1:3001/v1/consolidatedReport"
        data = {
            "start_date": self.start_date,
            "end_date": self.end_date
        }

        headers = {
            "X-API-Key": self.api_key
        }

        try:
            response = requests.post(url, json=data, headers=headers)

            if response.status_code == 200:
                print("Datos obtenidos exitosamente del backend.")
                return response.json()
            else:
                print(f"Error al hacer el llamado: {response.status_code}")
                print("Mensaje de error:", response.json())
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error en la solicitud al backend: {e}")
            return None

import requests
import io
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_restx import Api, Resource, fields
from general_report_consolidate import general_info, general_rates_by_date, general_rates_by_payments, general_rates_by_vehicle
from fpdf import FPDF
import pandas as pd
import matplotlib
matplotlib.use('pdf')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import seaborn as sns
import random
import os
import matplotlib.ticker as ticker
from fpdf import FPDF
from datetime import datetime, timedelta
import datetime as dt
import locale
from PIL import Image
from io import BytesIO
import base64
import pytz
import requests


# Define el modelo del payload
# Configuración de Flask y Flask-RESTx
app = Flask(__name__)
api = Api(app, doc="/docs")  # Ruta para la documentación de Swagger
generate_report_general_report_consolidated = api.model('GeneralReportPayload', {
    'start_date': fields.String(required=True, description='La fecha de inicio del reporte (formato ISO8601)'),
    'end_date': fields.String(required=True, description='La fecha de fin del reporte (formato ISO8601)'),
    'general_report_type': fields.String(required=False, default='Complete', description="El tipo de reporte ('Complete' o 'Summaries')"),
    'state': fields.String(required=False, description='El estado a filtrar en el reporte'),
    'toll': fields.String(required=False, description='El peaje a filtrar en el reporte'),
    'report_name': fields.String(required=False, description='El nombre del reporte'),
    'username': fields.String(required=False, description='El nombre de usuario del supervisor'),
})
ns = api.namespace("reports", description="Report Generation Endpoints")

AUTH_SERVICE_URL = "http://127.0.0.1:3001"  # Cambiar según sea necesario


venezuelan_hour = pytz.timezone('America/Caracas')

class Report_Generator(FPDF):

    def __init__(self, api_key, start_date, end_date):
        """
        Initializes the report object with the given parameters.

        This constructor sets up the initial state of the report object, including the date range, payment information, 
        toll state, toll information, supervisor information, and whether the report is complete or a summary. 
        It also adds custom fonts to be used in the report.

        Args:
            start_date (str): The start date of the report in ISO format.
            end_date (str): The end date of the report in ISO format.
            pago_directo_info (dict): Information related to direct payments.
            state (str or None): The state of the toll, if specified.
            toll (str or None): The toll information, if specified.
            supervisor_info (dict): Contains the supervisor's information, including 'name' and 'last_name'.
            complete (bool, optional): Indicates whether the report is complete or a summary. Defaults to True.

        Attributes:
            start_date (str): The start date of the report.
            end_date (str): The end date of the report.
            pago_directo_info (dict): Information related to direct payments.
            format_dot_comma (function): A function to format numbers with dots and commas.
            toll_state (str or None): The state of the toll, if specified.
            toll (str or None): The toll information, if specified.
            complete (bool): Indicates whether the report is complete or a summary.
            supervisor_info (dict): Contains the supervisor's information, including 'name' and 'last_name'.
        """
        def format_dot_comma(x, pos):
            """
            Formats numbers with dots and commas.

            Args:
                x (float): The number to format.
                pos (int): The position of the tick label.

            Returns:
                str: The formatted number as a string.
            """
            return str(locale.format_string('%.f',x,True))
        
        super().__init__()
        self.add_font('Arial', '', "./fonts/arial.ttf", uni=True)
        self.add_font('Arial', 'B', "./fonts/arial-bold.ttf", uni=True)
        self.api_key = api_key
        self.start_date = start_date
        self.end_date = end_date
        self.format_dot_comma = format_dot_comma
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
        
        apikey = self.authenticate_to_backend()
        
        headers = {
            "X-API-Key": apikey
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
    @staticmethod
    def authenticate_to_backend():
        """
        Realiza la autenticación al backend y devuelve el JSON generado.

        Returns:
            dict: El JSON de respuesta si la solicitud fue exitosa, None si no lo fue.
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
                return json_response.get("apiKey", {})
            else:
                print(f"Error al hacer el llamado: {response.status_code}")
                print("Mensaje de error:", response.json())
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error en la solicitud al backend: {e}")
            return None

    def general_rates_by_payment_types(self):
        """
        Generates a detailed report of payment methods and their respective rates.
        """
        print("LLego aqui ")

        # Obtener datos desde el backend
        json_data = self.fetch_data_from_backend()
        if not json_data:
            print("No se pudo obtener los datos del backend. No se generará el PDF.")
            return

        # Procesar los datos obtenidos
        try:
            # Verificar si la estructura de los datos es válida
            print("Paso por aqui")
            data = json_data.get("data", [])
            print("Paso por aqui")
            
            if not data:
                print("No se encontraron datos en la respuesta del backend.")
                return
            print("Paso por aqui")

            first_data_item = data[0]  # Obtener el primer item de la lista de datos
            results = first_data_item.get("data", {}).get("results", {})
            general_data = results.get("metodos_pago", {})
            print("Paso por aqui")

            if not general_data:
                print("No se pudieron obtener los datos de métodos de pago. No se generará el reporte.")
                return
            print("Paso por aqui")

            # Inicializar variables para los totales
            total_num_transactions = 0
            total_ves_amount = 0

            # Orden específico de los métodos de pago
            payment_order = [
                "Efectivo Bolívares", "Efectivo Dólares", "Efectivo Pesos", "Pago Móvil",
                "Punto de venta Bancamiga", "Punto de venta BNC", "Punto de venta Bicentenario",
                "Ventag", "VenVías", "Cobretag", "Pago Directo Bluetooth", "Exonerado", "Diferencial Cambiario"
            ]

            # Lista para almacenar los resultados
            table_data = [["Método de Pago", "N° Transacciones", "% Transacciones", "Monto Bs", "% Monto"]]
            print("Paso por aqui")

            # Acumular los totales y procesar datos
            for group in general_data.values():
                for data in group.values():
                    total_num_transactions += data.get('num_transactions', 0)
                    total_ves_amount += data.get("amount_pivoted", 0)
            print("Paso por aqui")

            # Generar filas respetando el orden de los métodos de pago
            for payment_name in payment_order:
                found = False
                for group in general_data.values():
                    for data in group.values():
                        if data.get("name") == payment_name:
                            # Agregar datos del método de pago
                            table_data.append([
                                payment_name,
                                locale.format_string('%.0f', data.get("num_transactions", 0), grouping=True),
                                f"{locale.format_string('%.2f', data.get('percentage_transactions', 0), grouping=True)}%",
                                locale.format_string('%.2f', data.get("amount_pivoted", 0), grouping=True),
                                f"{locale.format_string('%.2f', data.get('percentage_amount_collected', 0), grouping=True)}%",
                            ])
                            found = True
                            break
                    if found:
                        break

            # Agregar fila de totales
            table_data.append([
                "Totales",
                locale.format_string('%.0f', total_num_transactions, grouping=True),
                "",
                locale.format_string('%.2f', total_ves_amount, grouping=True),
                "",
            ])

        except (KeyError, IndexError) as e:
            print(f"Error al procesar los datos del backend: {str(e)}")
            return

        # Generar el PDF
        col_width_first_column = (self.w - 20) * 0.4
        col_width_others = (self.w - 20) * 0.15
        line_height = 8

        print("Add page")

        self.add_page()
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, subtitle, 0, 1, 'C')
        self.ln(10)

        for j, row in enumerate(table_data):
            for i, datum in enumerate(row):
                if j == 0:  # Encabezados
                    self.set_font('Arial', 'B', 10)
                    self.set_fill_color(200, 200, 200)
                elif j == len(table_data) - 1:  # Totales
                    self.set_font('Arial', 'B', 10)
                    self.set_fill_color(220, 220, 220)
                else:  # Filas normales
                    self.set_font('Arial', '', 9)
                    self.set_fill_color(255, 255, 255)

                col_width = col_width_first_column if i == 0 else col_width_others
                self.cell(col_width, line_height, datum, border=1, align='C', fill=True)
            self.ln(line_height)

        self.set_font('Arial', '', 12)

          
        def format_dot_comma(x, pos):
            """
            Formats numbers with dots and commas.

            Args:
                x (float): The number to format.
                pos (int): The position of the tick label.

            Returns:
                str: The formatted number as a string.
            """
            return str(locale.format_string('%.f',x,True))
        
        

    def header(self):
        """
        Generates the header section of the report.

        This method sets up the header for the report, including the logo, title, generation date, supervisor information, 
        date range, toll state, and toll information. The content and formatting of the header depend on whether the report 
        is complete or a summary.

        The header includes:
        - The Venpax logo.
        - The title of the report, which varies based on the completeness of the report.
        - The generation date and time.
        - The name and last name of the supervisor who requested the report.
        - The date range for the report.
        - The state of the toll, if specified.
        - The toll information, if specified.

        Attributes:
        - self.complete (bool): Indicates whether the report is complete or a summary.
        - self.supervisor_info (dict): Contains the supervisor's information, including 'name' and 'last_name'.
        - self.start_date (str): The start date of the report in ISO format.
        - self.end_date (str): The end date of the report in ISO format.
        - self.toll_state (str or None): The state of the toll, if specified.
        - self.toll (str or None): The toll information, if specified.

        Returns:
        - None
        """
        self.image('venpax-full-logo.png', 10, 8, 85)
        self.set_font('Arial', 'B', 16)
        self.set_text_color(40, 40, 40)
        # Move to the right
        self.set_x(100)

        self.cell(0,12, 'Resumen General de Recaudación',align='R',ln=1)
        self.set_font('Arial', 'B', 8.5)
        self.cell(208 - self.get_string_width(f'Generado el {datetime.strftime(datetime.now(venezuelan_hour), "%d/%m/%Y %H:%M:%S")}'), 5, 'Generado el ', 0, 0, 'R')
        self.set_font('Arial', '', 8.5)
        self.cell(0, 5, f' {datetime.strftime(datetime.now(venezuelan_hour), "%d/%m/%Y %H:%M:%S")}', 0, 1, align='R')

        self.cell(0,5, f'Del {datetime.strftime(datetime.fromisoformat(self.start_date), "%d/%m/%Y %H:%M:%S")} al {datetime.strftime(datetime.fromisoformat(self.end_date), "%d/%m/%Y %H:%M:%S")}',align='R', ln=1)

        self.set_font('Arial', 'B', 8.5)
        self.cell(203 - self.get_string_width(f'Estado: Todos'),5, 'Estado:  ',align='R')
        self.set_font('Arial', '', 8.5)
        self.cell(0, 5, f' Todos', 0, 1, align='R')

        self.set_font('Arial', 'B', 8.5)
        self.cell(203 - self.get_string_width(f'Peaje:   Todos'),5, 'Peaje:  ',align='R')
        self.set_font('Arial', '', 8.5)
        self.cell(0, 5, f' Todos', 0, 1, align='R')

        self.line(10, 48, 200, 48)
        self.ln(5)

    def footer(self):
        """
        Generates the footer section of the report.

        This method sets up the footer for the report, including a horizontal line and a text indicating the developer 
        and version information. The footer is positioned at the bottom of each page.

        The footer includes:
        - A horizontal line.
        - A text indicating the developer (Venpax, C.A) and the version information (2023 - 2024 / V1).

        Attributes:
        - self.h (float): The height of the page.

        Returns:
        - None
        """

        self.set_y(-15)
        self.set_line_width(0.2)
        self.line(10, self.h-15, 200, self.h-15)
        self.set_font('Arial', '', 6.5)
        self.cell(0, 10, 'Desarrollado por Venpax, C.A ® 2023 - 2024 / V1', 0, 0, 'C')

    def linechart_payments_and_amount_by_date(self):
        """
        Generates a line chart of payments and amounts collected by date.

        This method retrieves payment and amount data within a specified date range, processes the data, and generates 
        a line chart. The chart is saved as an image and included in the report.

        The chart includes:
        - A line plot of the number of payments by date.
        - A line plot of the amount collected by date.
        - Different time ranges (days, weeks, months) are handled to adjust the x-axis labels and data aggregation.

        Attributes:
        - self.start_date (str): The start date of the report.
        - self.end_date (str): The end date of the report.
        - self.pago_directo_info (dict): Information related to direct payments.
        - self.format_dot_comma (function): A function to format numbers with dots and commas.

        Returns:
        - None
        """

        # Retrieve general payment and amount information within the specified date range
        general_info = Tickets.get_tickets_total_amount_per_date_per_currency(start_date=self.start_date, end_date=self.end_date)
    
        fechas = []
        pagos = []
        amount = []

        # Process each entry in the retrieved information
        for i in general_info:

            # Check if the date exists in the pago directo info
            if i[0] in self.pago_directo_info[3]:
                pagos_daily = self.pago_directo_info[3][i[0]]['tickets'] + i[1]
                amount_daily = self.pago_directo_info[3][i[0]]['amount'] + i[2]
            else:
                pagos_daily  = i[1]
                amount_daily = float(i[2])

            # Append the processed data to the respective lists
            fechas.append(dt.datetime.strptime(i[0], '%Y-%m-%d').date())
            pagos.append(pagos_daily)
            amount.append(amount_daily)

        # Formatter for y-axis labels
        formatter = FuncFormatter(self.format_dot_comma)

        # Create a DataFrame from the processed data
        df = pd.DataFrame({'Fecha': fechas, 'Pagos': pagos, 'Monto': amount})
        df['Fecha'] = pd.to_datetime(df['Fecha'], format='%d-%m-%Y')

        # Calcular la diferencia en días entre la primera y última fecha
        dias_totales = (df['Fecha'].max() - df['Fecha'].min()).days
        
        if dias_totales > 3:
            
            # Definir los límites para los bindings
            limite_semanas = 30
            limite_meses = 90
            
            # Set up the plot style and context
            sns.set_style(style="whitegrid")
            sns.set_context("notebook")
            plt.rcParams.update({'font.family': 'Arial'}) 
            fig, ax = plt.subplots(nrows=2, ncols=1, figsize=(10, 6))
            bio = BytesIO() 

            # Set labels for the axes
            plt.xlabel('Rango de fechas', fontsize=12, fontweight='bold', labelpad=10)
            ax[0].set_ylabel('Cantidad de Vehículos', fontsize=12, fontweight='bold')  # Modifica el tamaño y establece negrita 
            ax[1].set_ylabel('Monto Recolectado', fontsize=12, fontweight='bold')    

            # Convert 'Fecha' column to datetime
            df['Fecha'] = pd.to_datetime(df['Fecha'], format='%d-%m-%Y')
            
            # Calculate the difference in days between the last two dates
            ultima_fecha = df['Fecha'].iloc[-1]
            penultima_fecha = df['Fecha'].iloc[-2]
            diferencia_dias = (ultima_fecha - penultima_fecha).days 

            # Set y-axis formatters
            ax[0].yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f'{x:,.0f}'.replace(',', 'X').replace('.', ',').replace('X', '.')))
            ax[1].yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f'Bs, {x:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')))

            # Handle different time ranges
            if dias_totales < 8:
                # For less than 8 days, plot by weekdays
                plt.xlabel('Rango de días', fontsize=12)
                weekdays = {
                    0:'Lunes',
                    1:'Martes',
                    2:'Miércoles',
                    3:'Jueves',
                    4:'Viernes',
                    5:'Sábado',
                    6:'Domingo'
                }
                plt.xticks( rotation=45, ha='center')

                df['Weekday'] = df['Fecha'].apply(lambda x: weekdays[x.weekday()])
                sns.lineplot( ax=ax[0],x=df['Weekday'].to_list(), y=df['Pagos'].to_list(), color="#FFC200", linewidth=2.5)
                sns.lineplot( ax=ax[1],x=df['Weekday'].to_list(), y=df['Monto'].to_list(), color="#FF7F50", linewidth=2.5)
                # ax[0].set_xticks( df_semanas['Weekday'].to_list() )
                # ax[0].set_xticks( df_semanas['Fecha'].to_list() )
                ax[0].set_xticklabels([])
                # ax[1].set_xticks( df_semanas['Fecha'].to_list() )
                plt.xticks( rotation=45, ha='center')
                ax[0].yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f'{x:,.0f}'.replace(',', 'X').replace('.', ',').replace('X', '.')))
                ax[1].yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f'Bs, {x:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')))
                

            elif dias_totales <= limite_semanas:
            
                # For up to 30 days, plot by individual dates
                ax[0].xaxis.set_major_locator(ticker.MaxNLocator(9))
                ax[1].xaxis.set_major_locator(ticker.MaxNLocator(9))
                df['Fecha'] = df['Fecha'].dt.strftime('%d-%m-%Y')
                sns.lineplot(ax=ax[0], x=df['Fecha'].to_list(), y=df['Pagos'].to_list(), color="#FFC200", linewidth=2.5)
                sns.lineplot(ax=ax[1], x=df['Fecha'].to_list(), y=df['Monto'].to_list(), color="#FF7F50", linewidth=2.5)
                ax[0].set_xticklabels([])
                plt.xticks( rotation=45, ha='center')
                ax[0].yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f'{x:,.0f}'.replace(',', 'X').replace('.', ',').replace('X', '.')))
                ax[1].yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f'Bs, {x:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')))
                
                
            elif dias_totales > limite_semanas and dias_totales < limite_meses:
        
                # For more than 30 days but less than 90 days, plot by weeks
                df_semanas = df.groupby(pd.Grouper(key='Fecha', freq='W-MON')).sum().reset_index()
                df_semanas['Fecha'] = df_semanas['Fecha'].dt.strftime('%d-%m-%Y')
                df['Fecha'] = df['Fecha'].dt.strftime('%d-%m-%Y')
                
                if diferencia_dias < 3:
                    df_semanas['Fecha'].to_list().pop(-2)

                sns.lineplot(ax=ax[0], x=df['Fecha'].to_list(), y=df['Pagos'].to_list(), color="#FFC200", linewidth=2.5)
                sns.lineplot(ax=ax[1], x=df['Fecha'].to_list(), y=df['Monto'].to_list(), color="#FF7F50", linewidth=2.5)
                
                ax[0].set_xticks( df_semanas['Fecha'].to_list() )
                ax[0].set_xticklabels([])
                ax[1].set_xticks( df_semanas['Fecha'].to_list() )
                plt.xticks( rotation=45, ha='center')
                ax[0].yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f'{x:,.0f}'.replace(',', 'X').replace('.', ',').replace('X', '.')))
                ax[1].yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f'Bs, {x:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')))
                
               

            elif dias_totales >= limite_meses:
                # For more than 90 days, plot by months
                
                df_meses = df.groupby(pd.Grouper(key='Fecha', freq='ME')).sum().reset_index()
                df_meses['Fecha'] = df_meses['Fecha'].dt.strftime('%d-%m-%Y')
                df['Fecha'] = df['Fecha'].dt.strftime('%d-%m-%Y')
                months = []
                for date in df_meses['Fecha'].to_list():
                    if date in df['Fecha'].to_list():
                        months.append(date)
                if df['Fecha'].to_list()[0] not in months:
                    months.insert(0, df['Fecha'].to_list()[0])
                if df['Fecha'].to_list()[-1] not in months:
                    months.append( df['Fecha'].to_list()[-1])

                if diferencia_dias < 3:
                    months.pop(-2)
                
                    
                sns.lineplot(x=df['Fecha'].to_list(), y=df['Pagos'].to_list(), color="#FFC200", linewidth=2.5, ax=ax[0])
                sns.lineplot(x=df['Fecha'].to_list(), y=df['Monto'].to_list(), color="#FF7F50", linewidth=2.5, ax=ax[1])
                ax[0].set_xticks(months)
                ax[0].set_xticklabels([])
                ax[1].set_xticks(months)
                plt.xticks( rotation=45, ha='center')
                plt.gca().yaxis.set_major_formatter(formatter)
                ax[0].yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f'{x:,.0f}'.replace(',', 'X').replace('.', ',').replace('X', '.')))
                ax[1].yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f'Bs, {x:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')))
                
            # Save the figure to a BytesIO object - In memory
            fig.savefig(bio, format="png", bbox_inches='tight')
            img_encoded = base64.b64encode(bio.getvalue()).decode()

            # Save the image to a temporary file
            with open("temp_img_line_collected.png", "wb") as f:
                f.write(base64.b64decode(img_encoded))

            # Add the image to the report
            self.ln(5)
            self.set_font('Arial', 'B', 11.5)
            self.set_fill_color(255,194,0)
            self.set_text_color(40,40,40)
            line_height = self.font_size * 2.5
            self.ln(5)
            self.cell(0, line_height, 'Gráficos de Accesos e Ingresos por Fechas', border=0, align='L', fill=True, ln=1)
            self.image("temp_img_line_collected.png", h=140, w=180)

            # Remove the temporary file
            os.remove("temp_img_line_collected.png")
            self.ln(10)

    def charts_vehicles2(self):
        """
        Generates and saves charts for vehicle payments within a specified date range.

        This function calculates the difference in days between the start and end dates,
        retrieves vehicle payment data, adjusts the data with direct payment info, and
        generates bar and pie charts to visualize the data. The charts are saved as images
        and added to a PDF report.

        Returns:
            None
        """

        date_format = "%Y-%m-%dT%H:%M:%S" 

        try:
            # Calculate the difference in days between the start and end dates
            start_date_dt = datetime.strptime(self.start_date, date_format)
            end_date_dt = datetime.strptime(self.end_date, date_format)
        except ValueError as e:
            print(f"Error en el formato de las fechas: {e}")
            return

        delta_days = (end_date_dt - start_date_dt).days

        
        # Retrieve vehicle payment data
        tarifas = Tickets.get_vehicles_general(self.start_date, self.end_date)

        # Adjust data with pafo directo info
        tarifas[1]["cantidad"] = tarifas[1]["cantidad"] + self.pago_directo_info[0]
        tarifas[1]["monto"] = tarifas[1]["monto"] + self.pago_directo_info[1]

        
        # Prepare data for DataFrame
        cantidad = []
        nombre = []
        monto = []
        for i in tarifas:
            monto.append(tarifas[i]['monto'])
            cantidad.append(tarifas[i]['cantidad'])
            nombre.append(tarifas[i]['nombre'])

        # Create DataFrames
        df_1 = pd.DataFrame({'Nombre': nombre, 'Cantidad': cantidad})
        df_2 = pd.DataFrame({'Nombre': nombre, 'Monto': monto})

        # Configure figure size
        bio = BytesIO()   

        # Vehicle order for sorting charts
        orden_vehiculos = {
            'Vehículo liviano': 1,
            'Microbús': 2,
            'Autobús': 3,
            'Camión liviano': 4,
            'Camión 2 ejes': 5,
            'Camión 3 ejes': 6,
            'Camión 4 ejes': 7,
            'Camión 5 ejes': 8,
            'Camión 6+ ejes': 9,
            'Exonerado General': 10,
            'Exonerado Ambulancia': 11,
            'Exonerado Seguridad': 12,
            'Exonerado Gobernación': 13,
            'Exonerado PDVSA': 14
        }

        df_1['Orden'] = df_1['Nombre'].map(orden_vehiculos)
        df_1_sorted = df_1.sort_values('Orden')

        df_2['Orden'] = df_2['Nombre'].map(orden_vehiculos)
        df_2_sorted = df_2.sort_values('Orden')

        # Check if the difference in days is less than 3
        if delta_days < 4:
            # Configure figure size and font
            plt.rcParams.update({'font.family': 'Arial'})
            fig = plt.figure(figsize=(16, 20))
            gs = fig.add_gridspec(2, 2, height_ratios=[2, 3])

            # Create horizontal bar charts
            ax0 = fig.add_subplot(gs[0, 0])
            ax1 = fig.add_subplot(gs[0, 1])
            ax2 = fig.add_subplot(gs[1, :])

            # Quantity chart
            sns.barplot(
                ax=ax0,
                x='Cantidad', 
                y='Nombre', 
                data=df_1_sorted,
                color="#FFCB26",
                saturation=1
            )
            ax0.set_title('Cantidad de Pagos por Tipo de Tarifa', fontsize=20, pad=20, loc='center', weight='bold')

            # Amount chart
            sns.barplot(
                ax=ax1,
                x='Monto', 
                y='Nombre', 
                data=df_2_sorted,
                color="#FFCB26",
                saturation=1
            )
            ax1.set_title('Monto de Pagos por Tipo de Tarifa', fontsize=20, pad=20, loc='center', weight='bold')

            # Rotate x-axis labels
            ax0.set_xticklabels(ax0.get_xticklabels(), rotation=45, ha='center')
            ax1.set_xticklabels(ax1.get_xticklabels(), rotation=45, ha='center')

            # Calculate totals for percentages
            total_cantidad = df_1_sorted['Cantidad'].sum()
            total_monto = df_2_sorted['Monto'].sum()

            # Add percentage labels above each bar
            for index, value in enumerate(df_1_sorted['Cantidad']):
                ax0.text(df_1_sorted['Cantidad'].max() * 0.05, index, f'{str(locale.format_string("%.f", value, True))} ({locale.format_string("%.2f", ((value / total_cantidad) * 100), True)}%)', va='center', fontsize=15, color='black', weight='bold')

            for index, value in enumerate(df_2_sorted['Monto']):
                ax1.text(df_2_sorted['Monto'].max() * 0.05, index, f'Bs. {str(locale.format_string("%.2f", value, True))} ({locale.format_string("%.2f", ((value / total_monto) * 100), True)}%)', va='center', fontsize=15, color='black', weight='bold')

            # Adjust axis limits and labels
            ax0.set_xlim(0, df_1_sorted['Cantidad'].max() * 1.2)
            ax1.set_xlim(0, df_2_sorted['Monto'].max() * 1.2)

            # Functions to format x-axis labels with thousand separators
            def thousands_cantidad(x, pos):
                return str(locale.format_string('%.f', x, True))

            def thousands_monto(x, pos):
                return str(locale.format_string('%.2f', x, True))

            formatter_cantidad = FuncFormatter(thousands_cantidad)
            formatter_monto = FuncFormatter(thousands_monto)

            # Apply formatter to x-axis
            ax0.xaxis.set_major_formatter(formatter_cantidad)
            ax1.xaxis.set_major_formatter(formatter_monto)
            

            # Add labels and titles with top margin
            ax0.set_xlabel('Cantidad de pagos', fontsize=19, labelpad=20, weight='bold')
            ax0.set_ylabel('Tarifas', fontsize=19, weight='bold')
            ax1.set_xlabel('Montos de pagos', fontsize=19, labelpad=20, weight='bold')
            ax1.set_ylabel('', fontsize=23, weight='bold')

            # Remove y-axis labels from the second bar chart
            ax1.set_yticklabels([])
            ax1.tick_params(left=False)
            ax0.tick_params(axis='both', which='major', labelsize=15)  # Para el eje x
            ax1.tick_params(axis='both', which='major', labelsize=15)  # Para el eje y

           
            
            ax0.grid(False)
            ax1.grid(False)

            # Add horizontal lines between bars
            for i in range(len(df_1_sorted)):
                ax0.axhline(y=i-0.5, color='grey', linewidth=0.8, linestyle='--')
                ax1.axhline(y=i-0.5, color='grey', linewidth=0.8, linestyle='--')

            # Add a border line to the chart
            for ax in [ax0, ax1]:
                ax.spines['top'].set_color('white')
                ax.spines['right'].set_color('white')
                ax.spines['left'].set_color('grey')
                ax.spines['bottom'].set_color('grey')

            # Custom Pie Chart
            plt.rcParams.update({'font.family': 'Arial'})

            # Colors for the pie chart
            color_palette = ['#FFC200', '#FF7F50', '#FF6B81', '#66CCCC', '#6699CC', '#FF8C00', '#99CCFF', '#66FF99', '#FF99CC', '#CC99FF', '#FF6348', '#FF69B4', '#FFFF99', '#99FF99']

            # Calculate percentages
            total = sum(df_1_sorted['Cantidad'])

            # Check if total is zero before calculating percentages
            if total == 0:
                porcentajes = [0] * len(df_1_sorted['Cantidad'])  # Asigna 0 a todos los porcentajes si el total es cero
            else:
                porcentajes = [(cantidad / total) * 100 for cantidad in df_1_sorted['Cantidad']]

            # Filter percentages less than 4% and replace with None
            for i, porcentaje in enumerate(porcentajes):
                if porcentaje < 4:
                    porcentajes[i] = None

            # Create the pie chart
            patches, _, _ = ax2.pie(
                df_1_sorted['Cantidad'], 
                labels=None, 
                autopct=lambda p: '{:.1f}%'.format(p) if p >= 4 else '', 
                colors=color_palette, 
                wedgeprops=dict(edgecolor='w', linewidth=1.5),
                textprops={'fontsize': 20},
                radius=0.9
            )

            # Add title
            ax2.set_title('Ingreso de Vehículos en Porcentaje', fontsize=24, loc='center', weight='bold')

            # Add legend to the left with larger font
            ax2.legend(patches, df_1_sorted['Nombre'], loc='center left', fontsize=15, bbox_to_anchor=(-0.3, 0.5))

            # Adjust space between subplots
            plt.subplots_adjust(hspace=20)


            plt.tight_layout()

            # Save the chart
            fig.savefig(bio, format="png", bbox_inches='tight')
            img_encoded = base64.b64encode(bio.getvalue()).decode()
            with open("temp_img_chart_collected_per_vehicles.png", "wb") as f:
                f.write(base64.b64decode(img_encoded))
            self.ln(5)
            self.set_font('Arial', 'B', 11.5)
            self.set_fill_color(255,194,0)
            self.set_text_color(40,40,40)
            line_height = self.font_size * 2.5
            self.cell(0, line_height, 'Gráficos de Vehículos', border=0, align='L', fill=True, ln=1)
            # Calcular la posición x para centrar la imagen en la página
            x_position = (216 - 120) / 2  # self.w es el ancho de la página
            self.ln(5)
            self.image("temp_img_chart_collected_per_vehicles.png", x=x_position, h=140, w=120)
            os.remove("temp_img_chart_collected_per_vehicles.png")
            self.ln(10)
            
            return
        
        # Configure figure size and font
        plt.rcParams.update({'font.family': 'Arial'})
        fig = plt.figure(figsize=(16, 20))
        gs = fig.add_gridspec(2, 2, height_ratios=[2, 3])

        # Create horizontal bar charts
        ax0 = fig.add_subplot(gs[0, 0])
        ax1 = fig.add_subplot(gs[0, 1])
        ax2 = fig.add_subplot(gs[1, :])

        # Quantity chart
        sns.barplot(
            ax=ax0,
            x='Cantidad', 
            y='Nombre', 
            data=df_1_sorted,
            color="#FFCB26",
            saturation=1
        )
        ax0.set_title('Cantidad y Porcentaje de Pagos por Categoría', fontsize=18, pad=20, loc='center', weight='bold')

        # Amount chart
        sns.barplot(
            ax=ax1,
            x='Monto', 
            y='Nombre', 
            data=df_2_sorted,
            color="#FFCB26",
            saturation=1
        )
        ax1.set_title('Monto y Porcentaje de Pagos por Categoría', fontsize=18, pad=20, loc='center', weight='bold')

        # Rotate x-axis labels
        ax0.set_xticklabels(ax0.get_xticklabels(), rotation=45, ha='center')
        ax0.xaxis.set_ticks_position('bottom') 
        ax1.set_xticklabels(ax1.get_xticklabels(), rotation=45, ha='center')
        ax1.xaxis.set_ticks_position('bottom')

        # Calculate totals for percentages
        total_cantidad = df_1_sorted['Cantidad'].sum()
        total_monto = df_2_sorted['Monto'].sum()

        # Add percentage labels above each bar
        for index, value in enumerate(df_1_sorted['Cantidad']):
            ax0.text(df_1_sorted['Cantidad'].max() * 0.05, index, f'{str(locale.format_string("%.f", value, True))} ({locale.format_string("%.2f", ((value / total_cantidad) * 100), True)}%)', va='center', fontsize=15, color='black', weight='bold')

        for index, value in enumerate(df_2_sorted['Monto']):
            ax1.text(df_2_sorted['Monto'].max() * 0.05, index, f'Bs. {str(locale.format_string("%.2f", value, True))} ({locale.format_string("%.2f", ((value / total_monto) * 100), True)}%)', va='center', fontsize=15, color='black', weight='bold')

        # Adjust axis limits and labels
        ax0.set_xlim(0, df_1_sorted['Cantidad'].max() * 1.2)
        ax1.set_xlim(0, df_2_sorted['Monto'].max() * 1.2)

        # Functions to format x-axis labels with thousand separators
        def thousands_cantidad(x, pos):
            return str(locale.format_string('%.f', x, True))

        def thousands_monto(x, pos):
            return str(locale.format_string('%.2f', x, True))

        formatter_cantidad = FuncFormatter(thousands_cantidad)
        formatter_monto = FuncFormatter(thousands_monto)

        # Apply formatter to x-axis
        ax0.xaxis.set_major_formatter(formatter_cantidad)
        ax1.xaxis.set_major_formatter(formatter_monto)

        # Add labels and titles with top margin
        ax0.set_xlabel('Cantidad de pagos', fontsize=17, labelpad=20, weight='bold')
        ax0.set_ylabel('Categorías', fontsize=17, weight='bold')
        ax1.set_xlabel('Monto Recolectado', fontsize=17, labelpad=20, weight='bold')
        ax1.set_ylabel('', fontsize=23, weight='bold')

        # Remove y-axis labels from the second bar chart
        ax1.set_yticklabels([])
        ax1.tick_params(left=False)
        ax0.tick_params(axis='both', which='major', labelsize=15)  # Para el eje x
        ax1.tick_params(axis='both', which='major', labelsize=15)  # Para el eje y
        # Rotate x-axis labels
        ax0.set_xticklabels(ax0.get_xticklabels(), rotation=45, ha='center')
        ax1.set_xticklabels(ax1.get_xticklabels(), rotation=45, ha='center')
        
        ax0.grid(False)
        ax1.grid(False)

        # Add horizontal lines between bars
        for i in range(len(df_1_sorted)):
            ax0.axhline(y=i-0.5, color='grey', linewidth=0.8, linestyle='--')
            ax1.axhline(y=i-0.5, color='grey', linewidth=0.8, linestyle='--')

        # Add a border line to the chart
        for ax in [ax0, ax1]:
            ax.spines['top'].set_color('white')
            ax.spines['right'].set_color('white')
            ax.spines['left'].set_color('grey')
            ax.spines['bottom'].set_color('grey')

        # Custom Pie Chart
        plt.rcParams.update({'font.family': 'Arial'})

        # Colors for the pie chart
        color_palette = ['#FFC200', '#FF7F50', '#FF6B81', '#66CCCC', '#6699CC', '#FF8C00', '#99CCFF', '#66FF99', '#FF99CC', '#CC99FF', '#FF6348', '#FF69B4', '#FFFF99', '#99FF99']

        # Calculate percentages
        total = sum(cantidad)
        porcentajes = [(cantidad / total) * 100 for cantidad in df_1_sorted['Cantidad']]

        # Filter percentages less than 4% and replace with None
        for i, porcentaje in enumerate(porcentajes):
            if porcentaje < 4:
                porcentajes[i] = None

        # Create the pie chart
        patches, _, _ = ax2.pie(
            df_1_sorted['Cantidad'], 
            labels=None, 
            autopct=lambda p: '{:.1f}%'.format(p) if p >= 4 else '', 
            colors=color_palette, 
            wedgeprops=dict(edgecolor='w', linewidth=1.5),
            textprops={'fontsize': 20}
        )

        # Set title
        ax2.set_title('Ingreso de Vehículos en Porcentaje', fontsize=24, loc='center', weight='bold' , pad=-500)

        # Add legend to the left with larger font
        ax2.legend(patches, df_1_sorted['Nombre'], loc='center left', fontsize=15, bbox_to_anchor=(-0.4, 0.5))

        # Adjust space between subplots
        plt.subplots_adjust(hspace=20)
        plt.tight_layout()

        # Save chart
        fig.savefig(bio, format="png", bbox_inches='tight')
        img_encoded = base64.b64encode(bio.getvalue()).decode()
        with open("temp_img_chart_collected_per_vehicles.png", "wb") as f:
            f.write(base64.b64decode(img_encoded))
        self.ln(5)
        self.set_font('Arial', 'B', 11.5)
        self.set_fill_color(255,194,0)
        self.set_text_color(40,40,40)
        line_height = self.font_size * 2.5
        self.cell(0, line_height, 'Gráficos de Vehículos', border=0, align='L', fill=True, ln=1)
        x_position = (216 - 180) / 2
        self.ln(5)
        self.image("temp_img_chart_collected_per_vehicles.png", x=x_position, h=200, w=180)

        os.remove("temp_img_chart_collected_per_vehicles.png")
        self.ln(10)

    def charts_vehicles(self):
        
        date_format = "%Y-%m-%dT%H:%M:%S" 

        try:
            # Calcular la diferencia de días entre las fechas de inicio y fin
            start_date_dt = datetime.strptime(self.start_date, date_format)
            end_date_dt = datetime.strptime(self.end_date, date_format)
        except ValueError as e:
            print(f"Error en el formato de las fechas: {e}")
            return

        delta_days = (end_date_dt - start_date_dt).days

        tarifas = Tickets.get_vehicles_general(self.start_date, self.end_date)
        
        tarifas[1]["cantidad"] = tarifas[1]["cantidad"] + self.pago_directo_info[0]
        tarifas[1]["monto"] = tarifas[1]["monto"] + self.pago_directo_info[1]
        
        cantidad = []
        nombre = []
        monto = []
        for i in tarifas:
            monto.append(tarifas[i]['monto'])
            cantidad.append(tarifas[i]['cantidad'])
            nombre.append(tarifas[i]['nombre'])

        # Crear DataFrames usando estas listas
        df_1 = pd.DataFrame({'Nombre': nombre, 'Cantidad': cantidad})
        df_2 = pd.DataFrame({'Nombre': nombre, 'Monto': monto})

        # Configuramos el tamaño de la figura
        bio = BytesIO()   

        # Orden de vehículos para ordenar las gráficas
        orden_vehiculos = {
            'Vehículo liviano': 1,
            'Microbús': 2,
            'Autobús': 3,
            'Camión liviano': 4,
            'Camión 2 ejes': 5,
            'Camión 3 ejes': 6,
            'Camión 4 ejes': 7,
            'Camión 5 ejes': 8,
            'Camión 6+ ejes': 9,
            'Exonerado General': 10,
            'Exonerado Ambulancia': 11,
            'Exonerado Seguridad': 12,
            'Exonerado Gobernación': 13,
            'Exonerado PDVSA': 14
        }

        df_1['Orden'] = df_1['Nombre'].map(orden_vehiculos)
        df_1_sorted = df_1.sort_values('Orden')

        df_2['Orden'] = df_2['Nombre'].map(orden_vehiculos)
        df_2_sorted = df_2.sort_values('Orden')

        # Configurar el tamaño de la figura y la fuente a Arial
        plt.rcParams.update({'font.family': 'Arial'})

        if delta_days > 3:
            fig, ax = plt.subplots(2, 2, figsize=(16, 17))
        else:
            fig, ax = plt.subplots(2, 2, figsize=(16, 12))

        # Crear gráficos de barras horizontales
        sns.barplot(
            ax=ax[0, 0],
            x='Cantidad', 
            y='Nombre', 
            data=df_1_sorted,
            color="#FFCB26",
            saturation=1
        )
        sns.barplot(
            ax=ax[0, 1],
            x='Monto', 
            y='Nombre', 
            data=df_2_sorted,
            color="#FFCB26",
            saturation=1
        )

        ax[0, 0].xaxis.set_ticks_position('bottom')  # Agregar ticks en la parte superior e inferior
        ax[0, 0].set_xticklabels(ax[0, 0].get_xticklabels(), rotation=45, ha='center')

        ax[0, 1].xaxis.set_ticks_position('bottom')  # Agregar ticks en la parte superior e inferior
        ax[0, 1].set_xticklabels(ax[0, 1].get_xticklabels(), rotation=45, ha='center')

        # Agregar títulos a cada gráfica
        ax[0, 0].set_title('Cantidad de Pagos por Categoría', fontsize=15, pad=20, loc='center', weight='bold')
        ax[0, 1].set_title('Monto de Pagos por Categoría', fontsize=15, pad=20, loc='center', weight='bold')

        # Calcular el total para los porcentajes
        total_cantidad = df_1_sorted['Cantidad'].sum()
        total_monto = df_2_sorted['Monto'].sum()

        # Añadir etiquetas de porcentaje encima de cada barra
        for index, value in enumerate(df_1_sorted['Cantidad']):
            ax[0, 0].text(df_1_sorted['Cantidad'].max() * 0.05, index, f'Total = {str(locale.format_string("%.f", value, True))}', va='center', fontsize=10, color='black', weight='bold')

        for index, value in enumerate(df_2_sorted['Monto']):
            ax[0, 1].text(df_2_sorted['Monto'].max() * 0.05, index, f'Bs. {str(locale.format_string("%.2f", value, True))}', va='center', fontsize=10, color='black', weight='bold')
        
        # Ajustar los límites de los ejes y las etiquetas
        ax[0, 0].set_xlim(0, df_1_sorted['Cantidad'].max() * 1.2)
        ax[0, 1].set_xlim(0, df_2_sorted['Monto'].max() * 1.2)

        # Funciones para formatear las etiquetas del eje x con separador de miles
        def thousands_cantidad(x, pos):
            return str(locale.format_string('%.f', x, True))

        def thousands_monto(x, pos):
            return str(locale.format_string('%.2f', x, True))

        formatter_cantidad = FuncFormatter(thousands_cantidad)
        formatter_monto = FuncFormatter(thousands_monto)

        # Aplicar el formateador al eje x
        ax[0, 0].xaxis.set_major_formatter(formatter_cantidad)
        ax[0, 1].xaxis.set_major_formatter(formatter_monto)

        # Añadir etiquetas y títulos con margen superior
        ax[0, 0].set_xlabel('Cantidad de pagos', fontsize=16, labelpad=20, weight='bold')
        ax[0, 0].set_ylabel('Categorías', fontsize=16, weight='bold', labelpad=20)
        ax[0, 1].set_xlabel('Monto Recolectado', fontsize=16, labelpad=20, weight='bold')
        ax[0, 1].set_ylabel('', fontsize=12, weight='bold')

        # Eliminar etiquetas del eje y de la segunda gráfica de barras
        ax[0, 1].set_yticklabels([])
        ax[0, 1].tick_params(left=False)
        ax[0, 0].grid(False)
        ax[0, 1].grid(False)

        # Añadir líneas horizontales entre las barras
        for i in range(len(df_1_sorted)):
            ax[0, 0].axhline(y=i-0.5, color='grey', linewidth=0.8, linestyle='--')
            ax[0, 1].axhline(y=i-0.5, color='grey', linewidth=0.8, linestyle='--')

        # Agregar gráficas de torta
       
        df_3 = pd.DataFrame({'Nombre': nombre, 'Cantidad': cantidad})
        df_4 = pd.DataFrame({'Nombre': nombre, 'Monto': monto})

        delta_days = (end_date_dt - start_date_dt).days

        colorPalette = [
                        '#FFC200', 
                        '#FF7F50', 
                        '#FF6B81',
                        '#66CCCC', 
                        '#6699CC', 
                        '#FF8C00', 
                        '#99CCFF', 
                        '#66FF99',
                        '#FF99CC', 
                        '#CC99FF', 
                        '#FF6348', 
                        '#FF69B4', 
                        '#FFFF99', 
                        '#99FF99'  
                    ]
        
        df_4['Orden'] = df_4['Nombre'].map(orden_vehiculos)

        def my_autopct(pct):
            return f'{pct:.1f}%' if pct > 4 else ''

        if delta_days > 3:
            ax[1, 0].pie(df_3['Cantidad'], labels=None, autopct=my_autopct, colors=colorPalette, wedgeprops=dict(edgecolor='w', linewidth=1.5), radius=1.3)
            ax[1, 1].pie(df_4['Monto'], labels=None, autopct=my_autopct, colors=colorPalette, wedgeprops=dict(edgecolor='w', linewidth=1.5), radius=1.3)
            plt.subplots_adjust(wspace=0.035, hspace=0.7)
            ax[1, 0].set_title('Porcentaje de Cantidad de Pagos por Categoría', fontsize=16, loc='left', weight='bold', x=-1.12, y=1.15)
            ax[1, 1].legend(loc='upper center', labels=df_4['Nombre'], bbox_to_anchor=(-0.6, -0.2), ncol=3, prop={'size': 15})

            ax[1, 1].set_title('Porcentaje de Monto de Pagos por Categoría', fontsize=16, loc='left', weight='bold', x=-0.26, y=1.15)
        else:
            ax[1, 0].pie(df_3['Cantidad'], labels=None, autopct=my_autopct, colors=colorPalette, wedgeprops=dict(edgecolor='w', linewidth=1.5), radius=1.1)
            ax[1, 1].pie(df_4['Monto'], labels=None, autopct=my_autopct, colors=colorPalette, wedgeprops=dict(edgecolor='w', linewidth=1.5), radius=1.1)
            plt.subplots_adjust(wspace=0.035, hspace=0.7)
            
            ax[1, 0].set_title('Porcentaje de Cantidad de Pagos por Categoría', fontsize=16, loc='left', weight='bold', x=-1.6, y=1.05)
            ax[1, 0].legend(loc='upper center', labels=df_4['Nombre'], bbox_to_anchor=(2.35, -0.1), ncol=3, prop={'size': 13})
            ax[1, 1].set_title('Porcentaje de Monto de Pagos por Categoría', fontsize=16, loc='left', weight='bold', x=-0.5, y=1.05)
 

        ax[1, 0].set_xlim(-0.1, 1)
        ax[1, 1].set_xlim(-0.8, 1)

        # Define el color para las líneas
        color_lineas1 = 'white'
        color_lineas2 = 'grey'

        # Añadir líneas horizontales entre las barras
        for i in range(len(df_1_sorted)):
            ax[0, 0].axhline(y=i-0.5, color=color_lineas2, linewidth=0.8, linestyle='--')
            ax[0, 1].axhline(y=i-0.5, color=color_lineas2, linewidth=0.8, linestyle='--')

        # Añadir una línea al borde de la gráfica
        for i in range(2):
            for j in range(2):
                ax[i, j].spines['top'].set_color(color_lineas1)
                ax[i, j].spines['right'].set_color(color_lineas1)
                ax[i, j].spines['bottom'].set_color(color_lineas2)
                ax[i, j].spines['left'].set_color(color_lineas2)
        
        # Mostramos el gráfico
        fig.savefig(bio, format="png", bbox_inches='tight')
        img_encoded = base64.b64encode(bio.getvalue()).decode()
        with open("temp_img_chart_collected_per_vehicles2.png", "wb") as f:
            f.write(base64.b64decode(img_encoded))
        self.ln(5)

        self.set_font('Arial', 'B', 11.5)
        self.set_fill_color(255,194,0)
        self.set_text_color(40,40,40)
        line_height = self.font_size * 2.5
        self.cell(0, line_height, 'Gráficos de Vehículos', border=0, align='L', fill=True, ln=1)

        self.ln(7)
        x_position = (216 - 180) / 2 

        if delta_days > 3:
            self.image("temp_img_chart_collected_per_vehicles2.png", x=x_position, h=200, w=180)
        else:
            self.image("temp_img_chart_collected_per_vehicles2.png", x=x_position, h=140, w=180)
        os.remove("temp_img_chart_collected_per_vehicles2.png")

    def charts_payments(self):

        metodos_pago_information = Payments.get_payment_type(self.start_date, self.end_date)
        metodos_pago_information[3]["pg"] = {
                                                "name":"Pago Directo Bluetooth",
                                                "amount":self.pago_directo_info[1],
                                                "num_transactions":self.pago_directo_info[0],
                                                "amount_pivoted":self.pago_directo_info[1]
                                            } 
        metodos_pago_information[3]['num_transactions'] = metodos_pago_information[3]['num_transactions'] + self.pago_directo_info[0]
        metodos_pago_information[3]['amount'] = metodos_pago_information[3]['amount'] + self.pago_directo_info[1]
        metodos_pago_information[3]['amount_pivoted'] = metodos_pago_information[3]['amount_pivoted'] + self.pago_directo_info[1]

        cantidad = []
        nombre = []
        montos = []
        cantidades_efectivo = []
        montos_efectivo = []
        nombre_efectivo = []
        for key,currencies in metodos_pago_information.items():
            if isinstance(currencies, dict):
                for key_2, payment_type in currencies.items():
                    if (((key == 1 or key == 2) and key_2 == 1) or key == 3) and isinstance(payment_type, dict):
                        cantidad.append(payment_type['num_transactions'])
                        nombre.append(payment_type['name'])
                        montos.append(payment_type['amount_pivoted'])
        
        cantidades_efectivo.append(metodos_pago_information[3]['num_transactions'])
        cantidades_efectivo.append(metodos_pago_information[2]['num_transactions'])
        cantidades_efectivo.append(metodos_pago_information[1]['num_transactions'])

        montos_efectivo.append(metodos_pago_information[3]['amount_pivoted'])
        montos_efectivo.append(metodos_pago_information[2]['amount_pivoted'])
        montos_efectivo.append(metodos_pago_information[1]['amount_pivoted'])

        nombre_efectivo.append('Bolívares')
        nombre_efectivo.append('Dólares')
        nombre_efectivo.append('Pesos')

        df_1 = pd.DataFrame({'Nombre': nombre, 'Cantidad': cantidad})
        df_2 = pd.DataFrame({'Nombre': nombre, 'Monto': montos})

        # Configuramos el tamaño de la figura
        bio = BytesIO()  

        orden_metodos_de_pago = {
            'Efectivo Bolívares': 1,
            'Efectivo Dólares': 2,
            'Efectivo Pesos': 3,
            'Pago Móvil': 4,
            'Punto de venta Bancamiga': 5,
            'Punto de venta BNC': 6,
            'Punto de venta Bicentenario': 7,
            'Ventag': 8,
            'VenVías': 9,
            'Cobretag': 10,
            'Pago Directo': 11,
            'Pago Directo Bluetooth': 12,
            'Exonerado': 13
        }
        df_1['Orden'] = df_1['Nombre'].map(orden_metodos_de_pago)
        df_1_sorted = df_1.sort_values('Orden')

        df_2['Orden'] = df_2['Nombre'].map(orden_metodos_de_pago)
        df_2_sorted = df_2.sort_values('Orden')

        # Configurar el tamaño de la figura y la fuente a Arial
        plt.rcParams.update({'font.family': 'Arial'})
        fig, ax = plt.subplots(2, 2, figsize=(16, 12))

        # Crear gráficos de barras horizontales
        sns.barplot(
            ax=ax[0, 0],
            x='Cantidad', 
            y='Nombre', 
            data=df_1_sorted,
            color="#FFCB26",
            saturation=1
        )
        sns.barplot(
            ax=ax[0, 1],
            x='Monto', 
            y='Nombre', 
            data=df_2_sorted,
            color="#FFCB26",
            saturation=1
        )

        ax[0, 0].xaxis.set_ticks_position('bottom')  # Agregar ticks en la parte superior e inferior
        ax[0, 0].set_xticklabels(ax[0, 0].get_xticklabels(), rotation=45, ha='center')

        ax[0, 1].xaxis.set_ticks_position('bottom')  # Agregar ticks en la parte superior e inferior
        ax[0, 1].set_xticklabels(ax[0, 1].get_xticklabels(), rotation=45, ha='center')

        # Agregar títulos a cada gráfica
        ax[0, 0].set_title('Cantidad de Pagos por Método de Pago', fontsize=15, pad=20, loc='center', weight='bold')
        ax[0, 1].set_title('Monto de Pagos por Método de Pago', fontsize=15, pad=20, loc='center', weight='bold')

        # Calcular el total para los porcentajes
        total_cantidad = df_1_sorted['Cantidad'].sum()
        total_monto = df_2_sorted['Monto'].sum()

        # Añadir etiquetas de porcentaje encima de cada barra
        for index, value in enumerate(df_1_sorted['Cantidad']):
            ax[0, 0].text(df_1_sorted['Cantidad'].max() * 0.05, index, f'Total = {str(locale.format_string("%.f", value, True))}', va='center', fontsize=10, color='black', weight='bold')

        for index, value in enumerate(df_2_sorted['Monto']):
            ax[0, 1].text(df_2_sorted['Monto'].max() * 0.05, index, f'Bs. {str(locale.format_string("%.2f", value, True))}', va='center', fontsize=10, color='black', weight='bold')

        # Ajustar los límites de los ejes y las etiquetas
        ax[0, 0].set_xlim(0, df_1_sorted['Cantidad'].max() * 1.2)
        ax[0, 1].set_xlim(0, df_2_sorted['Monto'].max() * 1.2)

        # Funciones para formatear las etiquetas del eje x con separador de miles
        def thousands_cantidad(x, pos):
            return str(locale.format_string('%.f', x, True))

        def thousands_monto(x, pos):
            return str(locale.format_string('%.2f', x, True))

        formatter_cantidad = FuncFormatter(thousands_cantidad)
        formatter_monto = FuncFormatter(thousands_monto)

        # Aplicar el formateador al eje x
        ax[0, 0].xaxis.set_major_formatter(formatter_cantidad)
        ax[0, 1].xaxis.set_major_formatter(formatter_monto)

        # Añadir etiquetas y títulos con margen superior
        ax[0, 0].set_xlabel('Cantidad de pagos', fontsize=16, labelpad=20, weight='bold')
        ax[0, 0].set_ylabel('Métodos de Pago', fontsize=16, weight='bold', labelpad=20)
        ax[0, 1].set_xlabel('Monto Recolectado', fontsize=16, labelpad=20, weight='bold')
        ax[0, 1].set_ylabel('', fontsize=12, weight='bold')

        # Eliminar etiquetas del eje y de la segunda gráfica de barras
        ax[0, 1].set_yticklabels([])
        ax[0, 1].tick_params(left=False)
        ax[0, 0].grid(False)
        ax[0, 1].grid(False)

        # Añadir líneas horizontales entre las barras
        for i in range(len(df_1_sorted)):
            ax[0, 0].axhline(y=i-0.5, color='grey', linewidth=0.8, linestyle='--')
            ax[0, 1].axhline(y=i-0.5, color='grey', linewidth=0.8, linestyle='--')

        # Agregar gráficas de torta
       
        df_3 = pd.DataFrame({'Nombre': nombre, 'Cantidad': cantidad})
        df_4 = pd.DataFrame({'Nombre': nombre_efectivo, 'Cantidad': cantidades_efectivo})
        orden_currency_cash = {
            'Bolívares': 1,
            'Dólares': 2,
            'Pesos': 3
        }
        orden_metodos_de_pago = {
            'Efectivo Bolívares': 1,
            'Efectivo Dólares': 2,
            'Efectivo Pesos': 3,
            'Pago Móvil': 4,
            'Punto de venta Bancamiga': 5,
            'Punto de venta BNC': 6,
            'Punto de venta Bicentenario': 7,
            'Ventag': 8,
            'VenVías': 9,
            'Cobretag': 10,
            'Pago Directo': 11,
            'Pago Directo Bluetooth': 12,
            'Exonerado': 13
        }
        if 'Ventag' not in df_3['Nombre'].values:
            df_3.loc[len(df_3.index)] = ['Ventag', 0] 
        if 'VenVías' not in df_3['Nombre'].values:
            df_3.loc[len(df_3.index)] = ['VenVías', 0] 
        if 'Cobretag' not in df_3['Nombre'].values:
            df_3.loc[len(df_3.index)] = ['Cobretag', 0] 
        if 'Pago Directo Bluetooth' not in df_3['Nombre'].values:
            df_3.loc[len(df_3.index)] = ['Pago Directo Bluetooth', 0] 
        if 'Punto de venta Bicentenario' not in df_3['Nombre'].values:
            df_3.loc[len(df_3.index)] = ['Punto de venta Bicentenario', 0]
        df_3['Orden'] = df_3['Nombre'].map(orden_metodos_de_pago)
        df_3 = df_3.sort_values('Orden')

        colorPalette = [
                        '#FFC200', 
                        '#FF7F50', 
                        '#FF6B81',
                        '#66CCCC', 
                        '#6699CC', 
                        '#FF8C00', 
                        '#99CCFF', 
                        '#66FF99',
                        '#FF99CC', 
                        '#CC99FF', 
                        '#FF6348', 
                        '#FF69B4', 
                        '#FFFF99', 
                        '#99FF99'  
                    ]
        
        df_4['Orden'] = df_4['Nombre'].map(orden_currency_cash)


        def my_autopct(pct):
            return f'{pct:.1f}%' if pct > 4 else ''

        ax[1, 0].pie(df_3['Cantidad'], labels=None, autopct=my_autopct, colors=colorPalette, wedgeprops=dict(edgecolor='w', linewidth=1.5))
        ax[1, 1].pie(df_4['Cantidad'], labels=None, autopct=my_autopct, colors=colorPalette, wedgeprops=dict(edgecolor='w', linewidth=1.5))

        # Ajustar el espacio entre subplots
        plt.subplots_adjust(wspace=0.035, hspace=0.7)

        ax[1, 0].set_xlim(-0.001, 1)
        ax[1, 1].set_xlim(-2, 1)

        # Añadir título y leyenda a los gráficos de torta
        ax[1, 0].set_title('Porcentaje de Recaudación por Método de Pago', fontsize=16, loc='left', weight='bold', x=-2.3)
        ax[1, 0].legend(loc='center left', labels=df_3['Nombre'], bbox_to_anchor=(-3.4, 0.5))

        ax[1, 1].set_title('Porcentaje de Recaudación por Tipo de Moneda', fontsize=16, loc='left', weight='bold', x=-0.1)
        ax[1, 1].legend(loc='center left', labels=df_4['Nombre'], bbox_to_anchor=(-0.135, 0.5))

        # Define el color para las líneas
        color_lineas1 = 'white'
        color_lineas2 = 'grey'

        # Añadir líneas horizontales entre las barras
        for i in range(len(df_1_sorted)):
            ax[0, 0].axhline(y=i-0.5, color=color_lineas2, linewidth=0.8, linestyle='--')
            ax[0, 1].axhline(y=i-0.5, color=color_lineas2, linewidth=0.8, linestyle='--')

        # Añadir una línea al borde de la gráfica
        for i in range(2):
            for j in range(2):
                ax[i, j].spines['top'].set_color(color_lineas1)
                ax[i, j].spines['right'].set_color(color_lineas1)
                ax[i, j].spines['bottom'].set_color(color_lineas2)
                ax[i, j].spines['left'].set_color(color_lineas2)

        # Mostramos el gráfico
        fig.savefig(bio, format="png", bbox_inches='tight')
        img_encoded = base64.b64encode(bio.getvalue()).decode()
        with open("temp_img_chart_collected_per_payments.png", "wb") as f:
            f.write(base64.b64decode(img_encoded))

        self.set_font('Arial', 'B', 11.5)
        self.set_fill_color(255,194,0)
        self.set_text_color(40,40,40)
        line_height = self.font_size * 2.5
        self.cell(0, line_height, 'Gráficos de Métodos de Pago', border=0, align='L', fill=True, ln=1)

        self.ln(5)
        x_position = (216 - 180) / 2 

        self.image("temp_img_chart_collected_per_payments.png", x=x_position, h=120, w=180)

        os.remove("temp_img_chart_collected_per_payments.png")
        self.ln(10)
        
    def barchart_vehicles_per_category(self):

        tarifas = Tickets.get_vehicles_general(self.start_date, self.end_date)
        
        tarifas[1]["cantidad"] = tarifas[1]["cantidad"] + self.pago_directo_info[0]
        tarifas[1]["monto"] = tarifas[1]["monto"] + self.pago_directo_info[1]
        
        cantidad = []
        nombre = []
        montos = []
        for i in tarifas:
            montos.append(tarifas[i]['monto'])
            cantidad.append(tarifas[i]['cantidad'])
            nombre.append(tarifas[i]['nombre'])

        # Tus datos de 'tarifas' ya están en las listas 'cantidad' y 'nombre'
        df = pd.DataFrame({'Nombre': nombre, 'Cantidad': cantidad})

        orden_vehiculos = {
            'Vehículo liviano': 1,
            'Microbús': 2,
            'Autobús': 3,
            'Camión liviano': 4,
            'Camión 2 ejes': 5,
            'Camión 3 ejes': 6,
            'Camión 4 ejes': 7,
            'Camión 5 ejes': 8,
            'Camión 6+ ejes': 9,
            'Exonerado General': 10,
            'Exonerado Ambulancia': 11,
            'Exonerado Seguridad': 12,
            'Exonerado Gobernación': 13,
            'Exonerado PDVSA': 14
        }
        df['Orden'] = df['Nombre'].map(orden_vehiculos)
        df_sorted = df.sort_values('Orden')

        # Configuramos el tamaño de la figura
        sns.set_style(style="whitegrid")
        sns.set_context("notebook")
        fig, ax = plt.subplots(figsize=(10, 6))
        bio = BytesIO()        

        # Creamos el gráfico de barras horizontales
        sns.barplot(
            x='Cantidad', 
            y='Nombre', 
            data=df_sorted,
            color="#FFCB26",
            saturation=1
        )

        # Calculamos el total para los porcentajes
        total = sum(df_sorted['Cantidad'])

        # Añadimos etiquetas de porcentaje al lado de cada barra
        for index, value in enumerate(df_sorted['Cantidad']):
            plt.text(10, index, f'{str(locale.format_string("%.f" ,value,True))} ({locale.format_string("%.2f",((value/total)*100),True)}%)', va='center')

        # Creamos una función para formatear las etiquetas del eje x con separador de miles
        def thousands(x, pos):
            'The two args are the value and tick position'
            return str(locale.format_string('%.f',x,True))

        formatter = FuncFormatter(thousands)

        # Aplicamos el formateador al eje x
        plt.gca().xaxis.set_major_formatter(formatter)

        # Eliminamos las etiquetas de los ejes si no son necesarias
        plt.xlabel('Cantidad de pagos', fontsize=15)
        plt.ylabel('Tarifas', fontsize=15)

        # Añadimos un título y ajustamos el layout
        plt.title(f'Tarifas por cantidad de pagos - {datetime.fromisoformat(self.start_date).strftime("%d/%m/%Y")} a {datetime.fromisoformat(self.end_date).strftime("%d/%m/%Y")}', fontsize=20)  # Puedes cambiarlo por el título que prefieras
        plt.tight_layout()

        # Mostramos el gráfico
        fig.savefig(bio, format="png", bbox_inches='tight')
        img_encoded = base64.b64encode(bio.getvalue()).decode()
        with open("temp_img_barchart_.png", "wb") as f:
            f.write(base64.b64decode(img_encoded))
        self.ln(5)
        self.image("temp_img_barchart_.png", h=105, w=180)

        os.remove("temp_img_barchart_.png")

        self.ln(5)

        # Tus datos de 'tarifas' ya están en las listas 'cantidad' y 'nombre'
        df = pd.DataFrame({'Nombre': nombre, 'Monto': montos})

        orden_vehiculos = {
            'Vehículo liviano': 1,
            'Microbús': 2,
            'Autobús': 3,
            'Camión liviano': 4,
            'Camión 2 ejes': 5,
            'Camión 3 ejes': 6,
            'Camión 4 ejes': 7,
            'Camión 5 ejes': 8,
            'Camión 6+ ejes': 9,
            'Exonerado General': 10,
            'Exonerado Ambulancia': 11,
            'Exonerado Seguridad': 12,
            'Exonerado Gobernación': 13,
            'Exonerado PDVSA': 14
        }
        df['Orden'] = df['Nombre'].map(orden_vehiculos)
        df_sorted = df.sort_values('Orden')
        # Configuramos el tamaño de la figura

        sns.set_style(style="whitegrid")
        sns.set_context("notebook")
        fig, ax = plt.subplots(figsize=(10, 6))
        bio = BytesIO()        

        # Creamos el gráfico de barras horizontales
        sns.barplot(
            x='Monto', 
            y='Nombre', 
            data=df_sorted,
            color="#FFCB26",
            saturation=1
        )


        # Calculamos el total para los porcentajes
        total = sum(df_sorted['Monto'])

        # Añadimos etiquetas de porcentaje al lado de cada barra
        for index, value in enumerate(df_sorted['Monto']):
            plt.text(120, index, f'Bs. {str(locale.format_string("%.2f" ,value,True))} ({locale.format_string("%.2f",((value/total)*100),True )}%)', va='center')

        # Creamos una función para formatear las etiquetas del eje x con separador de miles
        def thousands(x, pos):
            'The two args are the value and tick position'
            return str(locale.format_string('%.2f',x,True))

        formatter = FuncFormatter(thousands)

        # Aplicamos el formateador al eje x
        plt.gca().xaxis.set_major_formatter(formatter)

        # Eliminamos las etiquetas de los ejes si no son necesarias
        plt.xlabel('Montos de pagos', fontsize=15)
        plt.ylabel('Tarifas', fontsize=15)
        # Añadimos un título y ajustamos el layout
        plt.title(f'Tarifas por monto de pagos - {datetime.fromisoformat(self.start_date).strftime("%d/%m/%Y")} a {datetime.fromisoformat(self.end_date).strftime("%d/%m/%Y")}', fontsize=20)  # Puedes cambiarlo por el título que prefieras
        plt.tight_layout()

        # Mostramos el gráfico
        #fig.savefig(bio, format="png", bbox_inches='tight')
        #img_encoded = base64.b64encode(bio.getvalue()).decode()
        #with open("temp_img_barchart_collected_per_vehicles.png", "wb") as f:
         #   f.write(base64.b64decode(img_encoded))
        #self.ln(5)
        #self.image("temp_img_barchart_collected_per_vehicles.png", h=105, w=180)

        #os.remove("temp_img_barchart_collected_per_vehicles.png")
        #self.ln(10)

    def barchart_payment_types(self):

        metodos_pago_information = Payments.get_payment_type(self.start_date, self.end_date)
        metodos_pago_information

        

        metodos_pago_information[3]["pg"] = {
                                                "name":"Pago Directo Bluetooth",
                                                "amount":self.pago_directo_info[1],
                                                "num_transactions":self.pago_directo_info[0],
                                                "amount_pivoted":self.pago_directo_info[1]
                                            } 
        
        cantidad = []
        nombre = []
        montos = []
        for key,currencies in metodos_pago_information.items():
            if isinstance(currencies, dict):
                for key_2, payment_type in currencies.items():
                    if (((key == 1 or key == 2) and key_2 == 1) or key == 3) and isinstance(payment_type, dict):
                        cantidad.append(payment_type['num_transactions'])
                        nombre.append(payment_type['name'])
                        montos.append(payment_type['amount_pivoted'])
                        

        # Tus datos de 'tarifas' ya están en las listas 'cantidad' y 'nombre'
        df = pd.DataFrame({'Nombre': nombre, 'Cantidad': cantidad})

        orden_metodos_de_pago = {
            'Efectivo Bolívares': 1,
            'Efectivo Dólares': 2,
            'Efectivo Pesos': 3,
            'Pago Móvil': 4,
            'Punto de venta Bancamiga': 5,
            'Punto de venta BNC': 6,
            'Punto de venta Bicentenario': 7,
            'Ventag': 8,
            'VenVías': 9,
            'Cobretag': 10,
            'Pago Directo': 11,
            'Pago Directo Bluetooth': 12,
            'Exonerado': 13
        }
        df['Orden'] = df['Nombre'].map(orden_metodos_de_pago)
        df_sorted = df.sort_values('Orden')

        # Configuramos el tamaño de la figura
        sns.set_style(style="whitegrid")
        sns.set_context("notebook")
        fig, ax = plt.subplots(figsize=(10, 6))
        bio = BytesIO()        

        # Creamos el gráfico de barras horizontales
        sns.barplot(
            x='Cantidad', 
            y='Nombre', 
            data=df_sorted,
            color="#FFCB26",
            saturation=1
        )

        # Calculamos el total para los porcentajes
        total = sum(df_sorted['Cantidad'])

        # Añadimos etiquetas de porcentaje al lado de cada barra
        for index, value in enumerate(df_sorted['Cantidad']):
            plt.text(10, index, f'{str(locale.format_string("%.f" ,value,True))} ({locale.format_string("%.2f",((value/total)*100),True)}%)', va='center')

        # Creamos una función para formatear las etiquetas del eje x con separador de miles
        def thousands(x, pos):
            'The two args are the value and tick position'
            return str(locale.format_string('%.f',x,True))

        formatter = FuncFormatter(thousands)

        # Aplicamos el formateador al eje x
        plt.gca().xaxis.set_major_formatter(formatter)

        # Eliminamos las etiquetas de los ejes si no son necesarias
        plt.xlabel('Cantidad de pagos', fontsize=15)
        plt.ylabel('Métodos de pago', fontsize=15)

        # Añadimos un título y ajustamos el layout
        plt.title(f'Métodos de pago por cantidad de pagos - {datetime.fromisoformat(self.start_date).strftime("%d/%m/%Y")} a {datetime.fromisoformat(self.end_date).strftime("%d/%m/%Y")}', fontsize=20)  # Puedes cambiarlo por el título que prefieras
        plt.tight_layout()

        # Mostramos el gráfico
        fig.savefig(bio, format="png", bbox_inches='tight')
        img_encoded = base64.b64encode(bio.getvalue()).decode()
        with open("temp_img_barchart_payment_type_quantity.png", "wb") as f:
            f.write(base64.b64decode(img_encoded))
        self.ln(5)
        self.image("temp_img_barchart_payment_type_quantity.png", h=105, w=180)

        os.remove("temp_img_barchart_payment_type_quantity.png")

        self.ln(5)

        # Tus datos de 'tarifas' ya están en las listas 'cantidad' y 'nombre'
        df = pd.DataFrame({'Nombre': nombre, 'Monto': montos})

        orden_metodos_de_pago = {
            'Efectivo Bolívares': 1,
            'Efectivo Dólares': 2,
            'Efectivo Pesos': 3,
            'Pago Móvil': 4,
            'Punto de venta Bancamiga': 5,
            'Punto de venta BNC': 6,
            'Punto de venta Bicentenario': 7,
            'Ventag': 8,
            'VenVías': 9,
            'Cobretag': 10,
            'Pago Directo': 11,
            'Pago Directo Bluetooth': 12,
            'Exonerado': 13
        }
        df['Orden'] = df['Nombre'].map(orden_metodos_de_pago)
        df_sorted = df.sort_values('Orden')
        # Configuramos el tamaño de la figura

        sns.set_style(style="whitegrid")
        sns.set_context("notebook")
        fig, ax = plt.subplots(figsize=(10, 6))
        bio = BytesIO()        

        # Creamos el gráfico de barras horizontales
        sns.barplot(
            x='Monto', 
            y='Nombre', 
            data=df_sorted,
            color="#FFCB26",
            saturation=1
        )


        # Calculamos el total para los porcentajes
        total = sum(df_sorted['Monto'])

        # Añadimos etiquetas de porcentaje al lado de cada barra
        for index, value in enumerate(df_sorted['Monto']):
            plt.text(120, index, f'Bs. {str(locale.format_string("%.2f" ,value,True))} ({locale.format_string("%.2f",((value/total)*100),True )}%)', va='center')

        # Creamos una función para formatear las etiquetas del eje x con separador de miles
        def thousands(x, pos):
            'The two args are the value and tick position'
            return str(locale.format_string('%.2f',x,True))

        formatter = FuncFormatter(thousands)

        # Aplicamos el formateador al eje x
        plt.gca().xaxis.set_major_formatter(formatter)

        # Eliminamos las etiquetas de los ejes si no son necesarias
        plt.xlabel('Montos de pagos', fontsize=15)
        plt.ylabel('Métodos de pago', fontsize=15)
        # Añadimos un título y ajustamos el layout
        plt.title(f'Métodos de pago por monto de pagos - {datetime.fromisoformat(self.start_date).strftime("%d/%m/%Y")} a {datetime.fromisoformat(self.end_date).strftime("%d/%m/%Y")}', fontsize=20)  # Puedes cambiarlo por el título que prefieras
        plt.tight_layout()

        # Mostramos el gráfico
        fig.savefig(bio, format="png", bbox_inches='tight')
        img_encoded = base64.b64encode(bio.getvalue()).decode()
        with open("temp_img_barchart_collected_per_payment_type.png", "wb") as f:
            f.write(base64.b64decode(img_encoded))
        self.ln(5)
        self.image("temp_img_barchart_collected_per_payment_type.png", h=105, w=180)

        os.remove("temp_img_barchart_collected_per_payment_type.png")
        self.ln(10)

    def piechart_payment_types(self):
        metodos_pago_information = Payments.get_payment_type(self.start_date, self.end_date)
        metodos_pago_information

        

        metodos_pago_information[3]["pg"] = {
                                                "name":"Pago Directo Bluetooth",
                                                "amount":self.pago_directo_info[1],
                                                "num_transactions":self.pago_directo_info[0],
                                                "amount_pivoted":self.pago_directo_info[1]
                                            } 
        
        metodos_pago_information[3]['num_transactions'] = metodos_pago_information[3]['num_transactions'] + self.pago_directo_info[0]
        metodos_pago_information[3]['amount'] = metodos_pago_information[3]['amount'] + self.pago_directo_info[1]
        metodos_pago_information[3]['amount_pivoted'] = metodos_pago_information[3]['amount_pivoted'] + self.pago_directo_info[1]


        cantidad = []
        nombre = []
        montos = []
        cantidades_efectivo = []
        montos_efectivo = []
        nombre_efectivo = []
        for key,currencies in metodos_pago_information.items():
            if isinstance(currencies, dict):
                for key_2, payment_type in currencies.items():
                    if (((key == 1 or key == 2) and key_2 == 1) or key == 3) and isinstance(payment_type, dict):
                        cantidad.append(payment_type['num_transactions'])
                        nombre.append(payment_type['name'])
                        montos.append(payment_type['amount_pivoted'])
        cantidades_efectivo.append(metodos_pago_information[3]['num_transactions'])
        cantidades_efectivo.append(metodos_pago_information[2]['num_transactions'])
        cantidades_efectivo.append(metodos_pago_information[1]['num_transactions'])

        montos_efectivo.append(metodos_pago_information[3]['amount_pivoted'])
        montos_efectivo.append(metodos_pago_information[2]['amount_pivoted'])
        montos_efectivo.append(metodos_pago_information[1]['amount_pivoted'])

        nombre_efectivo.append('Efectivo Bolívares')
        nombre_efectivo.append('Efectivo Dólares')
        nombre_efectivo.append('Efectivo Pesos')

        # Tus datos de 'tarifas' ya están en las listas 'cantidad' y 'nombre'
        df = pd.DataFrame({'Nombre': nombre, 'Cantidad': cantidad})
        orden_metodos_de_pago = {
            'Efectivo Bolívares': 1,
            'Efectivo Dólares': 2,
            'Efectivo Pesos': 3,
            'Pago Móvil': 4,
            'Punto de venta Bancamiga': 5,
            'Punto de venta BNC': 6,
            'Punto de venta Bicentenario': 7,
            'Ventag': 8,
            'VenVías': 9,
            'Cobretag': 10,
            'Pago Directo': 11,
            'Pago Directo Bluetooth': 12,
            'Exonerado': 13
        }
        df = pd.DataFrame({'Nombre': nombre, 'Cantidad': cantidad})
        if 'Ventag' not in df['Nombre'].values:
            df.loc[len(df.index)] = ['Ventag', 0] 
        if 'VenVías' not in df['Nombre'].values:
            df.loc[len(df.index)] = ['VenVías', 0] 
        if 'Cobretag' not in df['Nombre'].values:
            df.loc[len(df.index)] = ['Cobretag', 0] 
        if 'Pago Directo Bluetooth' not in df['Nombre'].values:
            df.loc[len(df.index)] = ['Pago Directo Bluetooth', 0] 
        if 'Punto de venta Bicentenario' not in df['Nombre'].values:
            df.loc[len(df.index)] = ['Punto de venta Bicentenario', 0] 
        df['Orden'] = df['Nombre'].map(orden_metodos_de_pago)
        df = df.sort_values('Orden')
        colorPalette = [
                '#FFC200', 
                '#FF7F50', 
                '#FF6B81',
                '#66CCCC', 
                '#6699CC', 
                '#FF8C00', 
                '#99CCFF', 
                '#66FF99',
                '#FF99CC', 
                '#CC99FF', 
                '#FF6348', 
                '#FF69B4', 
                '#FFFF99', 
                '#99FF99'  
        ]


        fig, ax = plt.subplots(figsize=(8, 5), subplot_kw=dict(aspect="equal"))
        ax.pie(
                df['Cantidad'], 
                colors=colorPalette,
                autopct=lambda p: f'{str(locale.format_string("%.2f" ,p,True))}%' if p >=3.5 else ''
            )

        plt.legend(
            loc='center left', 
            labels=df['Nombre'],
            bbox_to_anchor=(1, 0, 0.5, 1)
        )

        plt.title('Porcentaje de Métodos de Pago', fontsize=20)
        sns.set_context('notebook')

        bio = BytesIO()
        fig.savefig(bio, format="png", bbox_inches='tight')
        img_encoded = base64.b64encode(bio.getvalue()).decode()
        with open("temp_img_piechart_payment_type.png", "wb") as f:
            f.write(base64.b64decode(img_encoded))
        self.ln(5)
        self.set_x(35)
        self.image("temp_img_piechart_payment_type.png", h=90, w=140)

        os.remove("temp_img_piechart_payment_type.png")

        self.ln(5)

        # Tus datos de 'tarifas' ya están en las listas 'cantidad' y 'nombre'
        df = pd.DataFrame({'Nombre': nombre_efectivo, 'Cantidad': cantidades_efectivo})
        orden_currency_cash = {
            'Efectivo Bolívares': 1,
            'Efectivo Dólares': 2,
            'Efectivo Pesos': 3
        }

        df['Orden'] = df['Nombre'].map(orden_currency_cash)
        colorPalette = [
                '#FFC200', 
                '#FF7F50', 
                '#66FF99'
        ]


        fig, ax = plt.subplots(figsize=(8, 5), subplot_kw=dict(aspect="equal"))
        ax.pie(
                df['Cantidad'], 
                colors=colorPalette,
                autopct=lambda p: f'{str(locale.format_string("%.2f" ,p,True))}%' if p >=3.5 else ''
            )

        plt.legend(
            loc='center left', 
            labels=df['Nombre'],
            bbox_to_anchor=(1, 0, 0.5, 1)
        )

        plt.title('Porcentaje de pagos por moneda', fontsize=20)
        sns.set_context('notebook')

        bio = BytesIO()
        fig.savefig(bio, format="png", bbox_inches='tight')
        img_encoded = base64.b64encode(bio.getvalue()).decode()
        with open("temp_img_piechart_cash.png", "wb") as f:
            f.write(base64.b64decode(img_encoded))
        self.ln(10)
        self.set_x(35)
        self.image("temp_img_piechart_cash.png", h=95, w=130)

        os.remove("temp_img_piechart_cash.png")

        self.ln(20)
    
    def general_info(self):
        """
        Genera y formatea la sección de información general del reporte.
        """
        # Obtenemos los datos directamente desde el backend
        json_data = self.fetch_data_from_backend()

        # Verificamos si la respuesta es válida
        if not json_data:
            print("No se pudo obtener los datos del backend. No se generará el PDF.")
            return

        # Procesar los datos obtenidos
        # Verificamos que la estructura de los datos sea la esperada
        try:
            # Obtenemos la lista 'data', y si no está vacía, tomamos el primer item
            first_data_item = json_data.get("data", [])[0]  # Obtener el primer elemento de la lista "data"
            results = first_data_item.get("data", {}).get("results", {})
            general_data = results.get("general_data", {})

            # Extraemos los datos relevantes, con valores por defecto en caso de que falten
            total_payments_bs = general_data.get("total_payments_bs", 0)
            total_payments_usd = general_data.get("total_payments_usd", 0)
            vehicles = general_data.get("vehicles", 0)

            # Preparamos los datos finales para mostrarlos en el reporte
            finals = [
                ('Monto Total en Bolívares', 'Monto Total en Dólares', 'Total de Vehículos'),
                (f"Bs. {locale.format_string('%2f',total_payments_bs, True)}", f"$ {locale.format_string('%2f',total_payments_usd, True)}", f"{vehicles:,}"),
            ]
        except (KeyError, IndexError) as e:
            print(f"Error al procesar los datos del backend: {str(e)}")
            return

        # Formatear los datos y añadirlos al PDF
        for j, row in enumerate(finals):
            for datum in row:
                if j == 0 or j == 2:
                    self.set_font('Arial', 'B', 13)
                    self.set_fill_color(255, 194, 0)
                    self.set_text_color(40, 40, 40)
                elif j == 1 or j == 3:
                    self.set_font('Arial', 'B', 12)
                    self.set_fill_color(255, 255, 255)
                    self.set_text_color(40, 40, 40)
                elif j == 4:
                    self.set_font('Arial', 'B', 12)
                    self.set_fill_color(235, 235, 235)
                    self.set_text_color(40, 40, 40)

                # Tamaño de la celda y contenido
                self.cell((self.w - 20) / len(row), 11, datum, 0, 0, 'C', fill=True)

            self.ln(11)  # Salto de línea tras cada fila

        # Resetear el formato de texto al predeterminado
        self.set_font('Arial', '', 12)


            
    def general_rates_by_date(self):
        """
        Generates a detailed report of access and income by date.
        """
        # Obtener datos desde el backend
        json_data = self.fetch_data_from_backend()
        if not json_data:
            print("No se pudo obtener los datos del backend. No se generará el PDF.")
            return

        # Procesar los datos obtenidos
        try:
            # Acceder al primer elemento de la respuesta (generalmente 'data' contiene una lista de resultados)
            first_data_item = json_data.get("data", [])[0]
            results = first_data_item.get("data", {}).get("results", {})
            general_data = results.get("fechas", {})  # Acceder a las fechas de los resultados

            # Inicializar los totales y la tabla de datos
            totals = {
                "pagos": 0,
                "monto": 0,
                "monto_usd": 0,
                "cash_ves": 0,
                "cash_usd": 0,
                "cash_cop": 0,
                "tc": 0,
            }
            table_data = [["Fecha", "Pagos", "Total General", "TC", "Total USD", "Efvo. Bs", "Efvo. USD", "Efvo. COP"]]

            # Procesar las filas de datos
            for date, details in general_data.items():
                pagos_daily = details.get("pagos", 0)
                amount_daily = details.get("monto", 0)
                exchange_rates = details.get("divisas", {})
                amount_daily_usd = exchange_rates.get("USD", {}).get("monto", 0)
                exchange_rate_tc = exchange_rates.get("USD", {}).get("tasa", 0)
                cash_collected = details.get("cash_collected", {})
                cash_ves = cash_collected.get("VES", 0)
                cash_usd = cash_collected.get("USD", 0)
                cash_cop = cash_collected.get("COP", 0)

                table_data.append([
                    datetime.fromisoformat(date).strftime('%d-%m-%Y'),
                    locale.format_string('%.0f', pagos_daily, grouping=True),
                    locale.format_string('%.2f', amount_daily, grouping=True),
                    locale.format_string('%.4f', exchange_rate_tc, grouping=True),
                    locale.format_string('%.2f', amount_daily_usd, grouping=True),
                    locale.format_string('%.2f', cash_ves, grouping=True),
                    locale.format_string('%.0f', cash_usd, grouping=True),
                    locale.format_string('%.0f', cash_cop, grouping=True),
                ])

                # Actualizar los totales
                totals["pagos"] += pagos_daily
                totals["monto"] += amount_daily
                totals["monto_usd"] += amount_daily_usd
                totals["cash_ves"] += cash_ves
                totals["cash_usd"] += cash_usd
                totals["cash_cop"] += cash_cop

            # Añadir los totales a la última fila
            table_data.append([
                "Totales",
                locale.format_string('%.0f', totals["pagos"], grouping=True),
                locale.format_string('%.2f', totals["monto"], grouping=True),
                
                locale.format_string('%.2f', totals["monto_usd"], grouping=True),
                locale.format_string('%.2f', totals["cash_ves"], grouping=True),
                locale.format_string('%.0f', totals["cash_usd"], grouping=True),
                locale.format_string('%.0f', totals["cash_cop"], grouping=True),
            ])
        except (KeyError, IndexError) as e:
            print(f"Error al procesar los datos del backend: {str(e)}")
            return

        # Formatear el informe en PDF
        col_width = (self.w - 20) / 8  # Ajustar ancho de columnas
        line_height = 8

        
        subtitle = "Resumen de Accesos e Ingresos por Fecha"
        self.subtitle_centered(subtitle)
        self.set_line_width(0)

        # Imprimir los datos en formato tabla
        for j,row in enumerate(table_data):
            for datum in row:

                if j == 0:
                    self.set_font('Arial', 'B', 8)
                    self.set_fill_color(255,194,0)
                    self.set_text_color(40,40,40)
                elif j == len(table_data)-1:
                    self.set_font('Arial', 'B', 8)
                    self.set_fill_color(235,235,235)
                    self.set_text_color(40,40,40)
                elif j%2 == 0:
                    self.set_font('Arial', '', 8)
                    self.set_fill_color(255,255,255)
                    self.set_text_color(40,40,40)
                elif j%2 == 1:
                    self.set_font('Arial', '', 8)
                    self.set_fill_color(249,249,249)
                    self.set_text_color(40,40,40)

                self.cell(col_width, line_height, datum, border=0,align='C', fill=True)
            self.ln(line_height)
     


    def general_rates_by_vehicle(self):
        """
        Generates a detailed report of vehicle rates.
        """
        # Obtener datos desde el backend
        json_data = self.fetch_data_from_backend()
        if not json_data:
            print("No se pudo obtener los datos del backend. No se generará el PDF.")
            return

        # Procesar los datos obtenidos
        try:
            first_data_item = json_data.get("data", [])[0]  # Obtener el primer elemento de la lista "data"
            results = first_data_item.get("data", {}).get("results", {})
            general_data = results.get("tarifas", {})

            if not general_data:
                print("No se pudieron obtener los datos de tarifas. No se generará el reporte.")
                return

            # Inicializar totales y datos de la tabla
            total_amount = total_ves_amount = total_pagos = total_ves_cash = total_usd_cash = total_cop_cash = 0
            table_data = [["Tipo de Vehículo", "Cantidad", "% Cantidad", "Monto Bs", "% Monto", "Efvo. Bs", "Efvo. USD", "Efvo. COP"]]

            # Calcular los totales
            for data in general_data.values():
                total_amount += data["cantidad"]
                total_ves_amount += data["monto"]
                total_pagos += data["cantidad"]
                total_ves_cash += data["cash_collected"]["VES"]
                total_usd_cash += data["cash_collected"]["USD"]
                total_cop_cash += data["cash_collected"]["COP"]

            # Añadir los datos a la tabla
            for data in general_data.values():
                amount = data["cantidad"]
                total = data["monto"]
                ves_cash = data["cash_collected"]["VES"]
                usd_cash = data["cash_collected"]["USD"]
                cop_cash = data["cash_collected"]["COP"]

                # Calcular porcentajes
                percentage_amount = (amount / total_amount) * 100
                percentage_ves_cash = (total / total_ves_amount) * 100

                table_data.append([
                    data["nombre"],
                    locale.format_string('%.0f', amount, grouping=True),
                    f"{locale.format_string('%.2f', percentage_amount, grouping=True)}%",
                    locale.format_string('%.2f', total, grouping=True),
                    f"{locale.format_string('%.2f', percentage_ves_cash, grouping=True)}%",
                    locale.format_string('%.2f', ves_cash, grouping=True),
                    locale.format_string('%.0f', usd_cash, grouping=True),
                    locale.format_string('%.0f', cop_cash, grouping=True),
                ])

            # Agregar fila de totales
            table_data.append([
                "Totales",
                locale.format_string('%.0f', total_pagos, grouping=True),
                "",
                locale.format_string('%.2f', total_ves_amount, grouping=True),
                "",
                locale.format_string('%.2f', total_ves_cash, grouping=True),
                locale.format_string('%.0f', total_usd_cash, grouping=True),
                locale.format_string('%.0f', total_cop_cash, grouping=True),
            ])
        except (KeyError, IndexError) as e:
            print(f"Error al procesar los datos del backend: {str(e)}")
            return

        # Formatear el informe en PDF
        col_width_first_column = (self.w - 20) * 0.3  # Ancho de la primera columna
        col_width_others = (self.w - 20) * 0.1  # Ancho de las demás columnas
        line_height = 8
        


        subtitle = "Resumen de Tarifas General"
        self.subtitle_centered(subtitle)
        self.set_line_width(0)

        # Imprimir los datos en formato tabla
        for j, row in enumerate(table_data):
            counter = 0
            for i, datum in enumerate(row):
                if j == 0:  # Encabezados
                    self.set_font('Arial', 'B', 8)
                    self.set_fill_color(255, 194, 0)
                    self.set_text_color(40, 40, 40)
                elif j == len(table_data) - 1:
                    self.set_font('Arial', 'B', 8)
                    self.set_fill_color(235, 235, 235)
                    self.set_text_color(40, 40, 40)
                elif j % 2 == 0:
                    self.set_font('Arial', '', 8)
                    self.set_fill_color(255, 255, 255)
                    self.set_text_color(40, 40, 40)
                elif j % 2 == 1:
                    self.set_font('Arial', '', 8)
                    self.set_fill_color(249, 249, 249)
                    self.set_text_color(40, 40, 40)

                if counter == 0:
                    self.cell(col_width_first_column, line_height, datum, border=0, align='C', fill=True)
                else:
                    self.cell(col_width_others, line_height, datum, border=0, align='C', fill=True)
                counter += 1
            self.ln(line_height)


    def general_rates_by_payment_types(self):
        """
        Generates a detailed report of payment methods and their respective rates.
        """
        print("LLego aqui ")
        subtitle = "Resumen de Métodos de Pago General"

        # Obtener datos desde el backend
        json_data = self.fetch_data_from_backend()
        if not json_data:
            print("No se pudo obtener los datos del backend. No se generará el PDF.")
            return

        # Procesar los datos obtenidos
        try:
            # Verificar si la estructura de los datos es válida
            print("Paso por aqui 1")
            data = json_data.get("data", [])
            print("Paso por aqui 2")

            if not data:
                print("No se encontraron datos en la respuesta del backend.")
                return
            print("Paso por aqui 3")

            first_data_item = data[0]  # Obtener el primer item de la lista de datos
            results = first_data_item.get("data", {}).get("results", {})
            general_data = results.get("metodos_pago", {})
            print("Paso por aqui 4")

            if not general_data:
                print("No se pudieron obtener los datos de métodos de pago. No se generará el reporte.")
                return
            print("Paso por aqui 5")

            # Inicializar variables para los totales
            total_num_transactions = 0
            total_ves_amount = 0

            # Orden específico de los métodos de pago
            payment_order = [
                "Efectivo Bolívares", "Efectivo Dólares", "Efectivo Pesos", "Pago Móvil",
                "Punto de venta Bancamiga", "Punto de venta BNC", "Punto de venta Bicentenario",
                "Ventag", "VenVías", "Cobretag", "Pago Directo Bluetooth", "Exonerado", "Diferencial Cambiario"
            ]

            # Lista para almacenar los resultados
            table_data = [["Método de Pago", "N° Transacciones", "% Transacciones", "Monto Bs", "% Monto"]]
            print("Paso por aqui 6")

            # Primero, acumular los totales por cada grupo (Dólares, Pesos, Bolívares)
            for group_key, group in general_data.items():
                if isinstance(group, dict):  # Verificamos que 'group' sea un diccionario
                    for payment_key, data in group.items():
                        if isinstance(data, dict):  # Verificamos que 'data' sea un diccionario
                            # Acumulando los totales
                            total_num_transactions += data.get('num_transactions', 0)
                            total_ves_amount += data.get("amount_pivoted", 0)
            print("Paso por aqui 7")

                # Ahora agregamos los detalles de cada método de pago a la lista 'finals', respetando el orden
            for payment_name in payment_order:
                # Buscar el método de pago en cada grupo
                found = False
                for group_key, group in general_data.items():
                    if isinstance(group, dict):
                        for payment_key, data in group.items():
                            if isinstance(data, dict) and data.get("name") == payment_name:
                                # Si encontramos el método de pago, lo agregamos
                                amount = data.get("num_transactions", 0)
                                total = data.get("amount_pivoted", 0)
                                percentage_transactions = data.get("percentage_transactions", 0)
                                percentage_amount_collected = data.get("percentage_amount_collected", 0)

                                table_data.append(
                                    (
                                        str(payment_name),
                                        str(locale.format_string('%.0f', amount, True)),
                                        f"{str(locale.format_string('%.2f', percentage_transactions, True))}%",
                                        str(locale.format_string('%.2f', total, True)),
                                        f"{str(locale.format_string('%.2f', percentage_amount_collected, True))}%",
                                    )
                                )
                                found = True
                                break
                    if found:
                        break
            print("Paso por aqui 8")

            # Agregar fila de totales
            table_data.append([
                "Totales",
                locale.format_string('%.0f', total_num_transactions, grouping=True),
                "",
                locale.format_string('%.2f', total_ves_amount, grouping=True),
                "",
            ])

        except (KeyError, IndexError) as e:
            print(f"Error al procesar los datos del backend: {str(e)}")
            return

        # Generar el PDF
        line_height = self.font_size * 2.5
        col_width = (self.w-20)/ 5

        subtitle = "Resumen de Métodos de Pago General"
        self.subtitle_centered(subtitle)
        self.set_line_width(0)

        for j, row in enumerate(table_data):
            for i, datum in enumerate(row):
                if j == 0:
                    self.set_font('Arial', 'B', 8)
                    self.set_fill_color(255,194,0)
                    self.set_text_color(40,40,40)
                elif j == len(table_data)-1:
                    self.set_font('Arial', 'B', 8)
                    self.set_fill_color(235,235,235)
                    self.set_text_color(40,40,40)
                elif j % 2 == 0:
                    self.set_font('Arial', '', 8)
                    self.set_fill_color(255,255,255)
                    self.set_text_color(40,40,40)
                elif j % 2 == 1:
                    self.set_font('Arial', '', 8)
                    self.set_fill_color(249,249,249)
                    self.set_text_color(40,40,40)

                self.cell(col_width, line_height, datum, border=0, align='C', fill=True)
            self.ln(line_height)

        self.set_font('Arial', '', 12)

    def general_by_currency(self):
        """
        Generates a detailed report of payments by currency.

        This method retrieves payment data, processes it to calculate totals per currency,
        and formats the data into a structured table. The table includes various financial metrics 
        such as total transactions, amounts in Bolívares, exchange rates, and subtotals.

        The table is then added to the report with appropriate formatting.

        Attributes:
        - self.start_date (str): The start date of the report.
        - self.end_date (str): The end date of the report.

        Returns:
        - None
        """

        payments_information = Payments.get_payments_currency_general(start_date=self.start_date, end_date=self.end_date)

        subtitle = 'Resumen de Divisas General'
        self.subtitle_centered(subtitle)
    
        # Set table header formatting
        self.set_fill_color(255,194,0)
        self.set_text_color(40,40,40)
        self.set_font('Arial', 'B', 8)
        self.cell((self.w-20)/6, 5, 'Nombre', 0, 0, 'C', fill=True)
        self.cell((self.w-20)/6, 5, 'Fecha', 0, 0, 'C', fill=True)
        self.cell((self.w-20)/6, 5, 'Cantidad', 0, 0, 'C', fill=True)
        self.cell((self.w-20)/6, 5, 'Bolívares', 0, 0, 'C', fill=True)
        self.cell((self.w-20)/6, 5, 'Tasa', 0, 0, 'C', fill=True)
        self.cell((self.w-20)/6, 5, 'Subtotal', 0, 1, 'C', fill=True)

        # Set table body formatting
        self.set_text_color(0,0,0)
        self.set_fill_color(255,255,255)
        self.set_font('Arial', '', 8)
        info_per_currency = {}

        # Process payment information
        for payment in payments_information:
            if payment[0] not in info_per_currency:
                info_per_currency[payment[0]] = {
                    'cantidad': 0,
                    'nombre': payment[0],
                    'amount': 0,
                    'amount_pivoted': 0
                }

            info_per_currency[payment[0]]['cantidad'] = info_per_currency[payment[0]]['cantidad'] + payment[4] 
            info_per_currency[payment[0]]['amount'] = info_per_currency[payment[0]]['amount'] + payment[5] 
            info_per_currency[payment[0]]['amount_pivoted'] = info_per_currency[payment[0]]['amount_pivoted'] + payment[6] 
    
            # Add payment details to the table
            self.cell((self.w-20)/6, 4, f'{payment[0]}', 0, 0, 'C', fill=True)
            self.cell((self.w-20)/6, 4, f'{datetime.strftime(payment[3], "%Y/%m/%d %H:%M:%S")}', 0, 0, 'C', fill=True)
            self.cell((self.w-20)/6, 4, f'{int(payment[4])}', 0, 0, 'C', fill=True)
            self.cell((self.w-20)/6, 4, f'{locale.format_string("%.2f" , payment[6], True)}', 0, 0, 'C', fill=True)
            if payment[1] == 1:
                self.cell((self.w-20)/6, 4, f'{locale.format_string("%.4f", payment[2], True)}', 0, 0, 'C', fill=True)
            elif payment[1] == 2:
                self.cell((self.w-20)/6, 4, f'{locale.format_string("%.8f", payment[2], True)}', 0, 0, 'C', fill=True)
            self.cell((self.w-20)/6, 4, f'{locale.format_string("%.2f" , payment[5], True)}', 0, 1, 'C', fill=True)
    
        # Set summary row formatting
        self.set_fill_color(255,194,0)
        self.set_text_color(40,40,40)
        self.set_font('Arial', 'B', 8)
        self.cell((self.w-20)/6, 5, 'Divisa', 0, 0, 'C', fill=True)
        self.cell((self.w-20)/6, 5, '', 0, 0, 'C', fill=True)
        self.cell((self.w-20)/6, 5, 'Cantidad', 0, 0, 'C', fill=True)
        self.cell((self.w-20)/6, 5, 'Bolívares', 0, 0, 'C', fill=True)
        self.cell((self.w-20)/6, 5, '', 0, 0, 'C', fill=True)
        self.cell((self.w-20)/6, 5, 'Total', 0, 1, 'C', fill=True)
        
        # Set summary row body formatting
        self.set_text_color(0,0,0)
        self.set_fill_color(255,255,255)
        self.set_font('Arial', '', 8)

        # Add summary details to the table
        for key, val in info_per_currency.items():
            self.cell((self.w-20)/6, 4, f'{key}', 0, 0, 'C', fill=True)
            self.cell((self.w-20)/6, 4, f'', 0, 0, 'C', fill=True)
            self.cell((self.w-20)/6, 4, f'{val["cantidad"]}', 0, 0, 'C', fill=True)
            self.cell((self.w-20)/6, 4, f'Bs. {locale.format_string("%.2f",val["amount_pivoted"], True)}', 0, 0, 'C', fill=True)
            self.cell((self.w-20)/6, 4, '', 0, 0, 'C', fill=True)
            self.cell((self.w-20)/6, 4, f'{locale.format_string("%.2f" , val["amount"], True)}', 0, 1, 'C', fill=True)
            
    def rates_by_date_by_channel(self):
        """
        Generates and formats a detailed report of ticket rates by date and channel.

        This method retrieves ticket data, processes it to calculate daily totals per channel,
        and formats the data into a structured table. The table includes various financial metrics
        such as total payments, total amounts in different currencies, and cash amounts.

        The table is then added to the report with appropriate formatting.

        Attributes:
        - self.start_date (str): The start date of the report.
        - self.end_date (str): The end date of the report.
        - self.pago_directo_info (dict): Information related to direct payments.

        Returns:
        - None
        """
        # Retrieve ticket data per date, currency, and channel
        all_info = Tickets.get_tickets_total_amount_per_date_per_currency_per_channel(start_date=self.start_date, end_date=self.end_date)
        info_per_channel = {}

        line_height = self.font_size * 2.5
        col_width = (self.w-20)/ 8

        # Organize data by channel 
        for i in all_info:
            if i[1] not in info_per_channel:
                info_per_channel[i[1]] = {"info":[], "name": i[2]}
                info_per_channel[i[1]]["info"].append(i)
            else:
                info_per_channel[i[1]]["info"].append(i)

        # Sort channels by name
        info_per_channel = dict(sorted(info_per_channel.items(), key=lambda item: item[1]['name']))
        for elem in info_per_channel:
            self.subtitle_centered(f'Resumen de Accesos e Ingresos por Fecha - Canal {info_per_channel[elem]["name"]}')

            general_info = info_per_channel[elem]["info"]

            pago_directo_channel_daily = {}
            if int(info_per_channel[elem]["name"]) in self.pago_directo_info[4]:
                pago_directo_channel_daily = self.pago_directo_info[4][int(info_per_channel[elem]["name"])]

            total_pagos = 0
            total_amount = 0
            total_amount_usd = 0
            total_cash_ves = 0
            total_cash_usd = 0
            total_cash_cop = 0
 
            finals = [('Fecha', 'Pagos', 'Total general', 'TC', 'Total USD', 'Efvo. Bs', 'Efvo. USD', 'Efvo. COP')]

            # Process each entry in the general info
            for i in general_info:
                if i[0] in pago_directo_channel_daily:
                    pagos_daily = pago_directo_channel_daily[i[0]]['tickets'] + i[3]
                    amount_daily = pago_directo_channel_daily[i[0]]['amount'] + float(i[4])
                    amount_daily_usd = pago_directo_channel_daily[i[0]]['amount']/float(i[5]) + float(i[6])
                else:
                    pagos_daily = i[3]
                    amount_daily = float(i[4])
                    amount_daily_usd = float(i[6])

                finals.append(
                    (
                        str(datetime.fromisoformat(i[0]).strftime('%d-%m-%Y')), 
                        str(locale.format_string('%.0f',pagos_daily, True)), 
                        str(locale.format_string('%.2f',amount_daily, True)), 
                        str(locale.format_string('%.2f',float(i[5]), True)), 
                        str(locale.format_string('%.2f',amount_daily_usd, True)), 
                        str(locale.format_string('%.2f',float(i[9]), True)), 
                        str(locale.format_string('%.0f',float(i[7]), True)),
                        str(locale.format_string('%.0f',float(i[8]), True))
                        )
                )
                total_pagos += pagos_daily
                total_amount += amount_daily
                total_amount_usd += amount_daily_usd
                total_cash_usd += float(i[7])
                total_cash_cop += float(i[8])
                total_cash_ves += float(i[9])

            # Append totals to the final data structure
            finals.append(
                (
                    '', 
                    str(locale.format_string('%d', total_pagos, True)), 
                    str(locale.format_string('%.2f', total_amount, True)), 
                    '', 
                    str(locale.format_string('%.2f', total_amount_usd, True)), 
                    str(locale.format_string('%.2f', total_cash_ves, True)), 
                    str(locale.format_string('%d', total_cash_usd, True)),
                    str(locale.format_string('%d', total_cash_cop, True))
                )
            )

            # Format and add the final data to the report
            for j,row in enumerate(finals):
                for datum in row:

                    if j == 0:
                        self.set_font('Arial', 'B', 8)
                        self.set_fill_color(255,194,0)
                        self.set_text_color(40,40,40)
                    elif j == len(finals)-1:
                        self.set_font('Arial', 'B', 8)
                        self.set_fill_color(235,235,235)
                        self.set_text_color(40,40,40)
                    elif j%2 == 0:
                        self.set_font('Arial', '', 8)
                        self.set_fill_color(255,255,255)
                        self.set_text_color(40,40,40)
                    elif j%2 == 1:
                        self.set_font('Arial', '', 8)
                        self.set_fill_color(249,249,249)
                        self.set_text_color(40,40,40)

                    self.cell(col_width, line_height, datum, border=0,align='C', fill=True)
                self.ln(line_height)

    def rates_by_vehicle_by_channel(self):
        """
        Generates and formats a detailed report of ticket rates by vehicle type and channel.

        This method retrieves ticket data, processes it to calculate totals per vehicle type and channel,
        and formats the data into a structured table. The table includes various financial metrics
        such as total payments, total amounts in different currencies, and cash amounts.

        The table is then added to the report with appropriate formatting.

        Attributes:
        - self.start_date (str): The start date of the report.
        - self.end_date (str): The end date of the report.
        - self.pago_directo_info (dict): Information related to direct payments.

        Returns:
        - None
        """
        # Retrieve ticket data per vehicle, currency, and channel
        all_info = Tickets.get_tickets_total_amount_per_vehicle_per_currency_per_channel(start_date=self.start_date, end_date=self.end_date)
        info_per_channel = {}

        line_height = self.font_size * 2.5
        col_width_first_column = 35.625
        col_width_others = (self.w - 20 - col_width_first_column) / 7    # Adjust column width for 8 columns instead of 10

        # Organize data by channel
        for i in all_info:
            if i[8] not in info_per_channel:
                info_per_channel[i[8]] = {"info": [], "name": i[9]}
                info_per_channel[i[8]]["info"].append(i)
            else:
                info_per_channel[i[8]]["info"].append(i)

        # Sort channels by name
        info_per_channel = dict(sorted(info_per_channel.items(), key=lambda item: item[1]['name']))
        for elem in info_per_channel:
            self.subtitle_centered(f'Resumen de Accesos e Ingresos por Vehículo - Canal {info_per_channel[elem]["name"]}')
            general_info = info_per_channel[elem]["info"]

            if int(info_per_channel[elem]["name"]) in self.pago_directo_info[2]:
                pago_directo_channel_by_vehicle = self.pago_directo_info[2][int(info_per_channel[elem]["name"])]
            else:
                pago_directo_channel_by_vehicle = {'tickets': 0, 'amount': 0}

            total_pagos = 0
            total_amount = 0
            total_amount_usd = 0
            total_ves_cash = 0
            total_usd_cash = 0
            total_cop_cash = 0

            # Process each entry in the general info
            for i in general_info:
                total_pagos += i[5]
                total_amount += float(i[3])
                total_amount_usd += float(i[4])
                total_ves_cash += float(i[12])
                total_usd_cash += float(i[10])
                total_cop_cash += float(i[11])

            total_pagos += pago_directo_channel_by_vehicle['tickets']
            total_amount += pago_directo_channel_by_vehicle['amount']

            finals = []
            for i in general_info:
                if 'Vehículo liviano' == i[0]:
                    vehicle_pagos = i[5] + pago_directo_channel_by_vehicle['tickets']
                    vehicle_amount = float(i[3]) + pago_directo_channel_by_vehicle['amount']
                    vehicle_amount_usd = float(i[4]) + pago_directo_channel_by_vehicle['amount'] / i[2]
                else:
                    vehicle_pagos = i[5]
                    vehicle_amount = float(i[3])
                    vehicle_amount_usd = float(i[4])
                if total_pagos > 0:
                    percentage_pagos = (vehicle_pagos / total_pagos) * 100
                else:
                    percentage_pagos = 0

                if total_amount > 0:
                    percentage_amount = (vehicle_amount / total_amount) * 100
                else:
                    percentage_amount = 0
                finals.append(
                    (
                        str(i[0]),
                        str(locale.format_string('%.0f', vehicle_pagos, True)),
                        f"{str(locale.format_string('%.2f', percentage_pagos, True))}%",
                        str(locale.format_string('%.2f', vehicle_amount, True)),
                        f"{str(locale.format_string('%.2f', percentage_amount, True))}%",
                        f"{str(locale.format_string('%.2f', i[12], True))}",
                        f"{str(locale.format_string('%.0f', i[10], True))}",
                        f"{str(locale.format_string('%.0f', i[11], True))}"
                    )
                )
            orden_vehiculos = {
                'Vehículo liviano': 1,
                'Microbús': 2,
                'Autobús': 3,
                'Camión liviano': 4,
                'Camión 2 ejes': 5,
                'Camión 3 ejes': 6,
                'Camión 4 ejes': 7,
                'Camión 5 ejes': 8,
                'Camión 6+ ejes': 9,
                'Exonerado General': 10,
                'Exonerado Ambulancia': 11,
                'Exonerado Seguridad': 12,
                'Exonerado Gobernación': 13,
                'Exonerado PDVSA': 14
            }

            finals = sorted(finals, key=lambda x: orden_vehiculos[x[0]] if x[0] in orden_vehiculos else len(finals))
            finals = [('Tipo de Vehículo', 'Pagos', '% pagos', 'Total Bs', '% Monto', 'Efvo. Bs', 'Efvo. USD', 'Efvo. COP')] + finals
            finals.append(
                (
                    '',
                    str(locale.format_string('%.0f', total_pagos, True)),
                    '',
                    str(locale.format_string('%.2f', total_amount, True)),
                    '',
                    str(locale.format_string('%.2f', total_ves_cash, True)),
                    str(locale.format_string('%.0f', total_usd_cash, True)),
                    str(locale.format_string('%.0f', total_cop_cash, True))
                )
            )

            # Format and add the final data to the report
            for j, row in enumerate(finals):
                counter = 0
                for datum in row:
                    if j == 0:
                        self.set_font('Arial', 'B', 8)
                        self.set_fill_color(255, 194, 0)
                        self.set_text_color(40, 40, 40)
                    elif j == len(finals) - 1:
                        self.set_font('Arial', 'B', 8)
                        self.set_fill_color(235, 235, 235)
                        self.set_text_color(40, 40, 40)
                    elif j % 2 == 0:
                        self.set_font('Arial', '', 8)
                        self.set_fill_color(255, 255, 255)
                        self.set_text_color(40, 40, 40)
                    elif j % 2 == 1:
                        self.set_font('Arial', '', 8)
                        self.set_fill_color(249, 249, 249)
                        self.set_text_color(40, 40, 40)

                    if counter == 0:
                        self.cell(col_width_first_column, line_height, datum, border=0, align='C', fill=True)
                    else:
                        self.cell(col_width_others, line_height, datum, border=0, align='C', fill=True)
                    counter += 1
                self.ln(line_height)

    def rates_by_payment_types_by_channel(self):
        """
        Generates and formats a detailed report of payment types by channel.

        This method retrieves payment type data and ticket data, processes it to calculate totals per payment type and channel,
        and formats the data into a structured table. The table includes various financial metrics such as total transactions,
        total amounts, and percentages of transactions and amounts collected.

        The table is then added to the report with appropriate formatting.

        Attributes:
        - self.start_date (str): The start date of the report.
        - self.end_date (str): The end date of the report.
        - self.pago_directo_info (dict): Information related to direct payments.

        Returns:
        - None
        """
        # Retrieve payment type data per channel
        general_info = Payments.get_payment_type_per_channel(start_date=self.start_date, end_date=self.end_date)
        # Retrieve ticket data per vehicle, currency, and channel

        all_info = Tickets.get_tickets_total_amount_per_vehicle_per_currency_per_channel(start_date=self.start_date, end_date=self.end_date)
        info_per_channel = {}
        line_height = self.font_size * 2.5
        col_width = (self.w - 20) / 5
        
        # Organize data by channel
        for i in all_info:
            channel_id = int(i[9])
            if channel_id not in info_per_channel:
                info_per_channel[channel_id] = {"info": [], "name": i[9], "id": i[8]}
            info_per_channel[channel_id]["info"].append(i)

        # Sort channels by name
        info_per_channel = dict(sorted(info_per_channel.items(), key=lambda item: item[1]['name']))

        for key, val in general_info.items():
            total_transactions = 0
            total_amount = 0
            general_info2 = info_per_channel[int(key)]["info"]

            # Calculate total_amount2 once
            total_amount2 = sum(float(info[3]) for info in general_info2)
            
            # Add direct payment amount if present
            if int(info_per_channel[int(key)]["name"]) in self.pago_directo_info[2]:
                pago_directo_channel_by_vehicle = self.pago_directo_info[2][int(info_per_channel[int(key)]["name"])]
                total_amount2 += pago_directo_channel_by_vehicle['amount']

            # Calculate total transactions and amount collected by payment method
            for key_2, val_2 in val.items():
                for key_3, val_3 in val_2.items():
                    if key_3 != 'currency_name':
                        total_transactions += val_3['num_transactions']
                        total_amount += float(val_3['amount_pivoted'])

            # Add pago directo Bluetooth payment info if present
            if int(key) in self.pago_directo_info[2]:
                total_transactions += self.pago_directo_info[2][int(key)]['tickets']
                total_amount += self.pago_directo_info[2][int(key)]['amount']
            
                general_info[key][3]['pg'] = {
                    "name": "Pago Directo Bluetooth",
                    "amount": self.pago_directo_info[2][int(key)]['amount'],
                    "num_transactions": self.pago_directo_info[2][int(key)]['tickets'],
                    "amount_pivoted": self.pago_directo_info[2][int(key)]['amount'],
                    "percentage_transactions": (self.pago_directo_info[2][int(key)]['tickets'] / total_transactions) * 100 if total_transactions > 0 else 0,
                    "percentage_amount_collected": (self.pago_directo_info[2][int(key)]['amount'] / total_amount2) * 100 if total_amount2 > 0 else 0
                } 
            else:
                general_info[key][3]['pg'] = {
                    "name": "Pago Directo Bluetooth",
                    "amount": 0,
                    "num_transactions": 0,
                    "amount_pivoted": 0,
                    "percentage_transactions": 0,
                    "percentage_amount_collected": 0
                } 

            # Update total_amount and total_transactions in general_info
            general_info[key]['total_amount'] = total_amount
            general_info[key]['total_transactions'] = total_transactions

            # Generate report for each channel
            self.subtitle_centered(f'Resumen de Métodos de Pago General- Canal {key}')
            finals = []

            for key_2, val_2 in val.items():
                if key_2 == 1 or key_2 == 2:
                    if total_transactions > 0:
                        val_2[1]['percentage_transactions'] = (float(val_2[1]['num_transactions']) / total_transactions) * 100
                    else:
                        val_2[1]['percentage_transactions'] = 0

                    if total_amount2 > 0:
                        val_2[1]['percentage_amount_collected'] = (float(val_2[1]['amount_pivoted']) / total_amount2) * 100
                    else:
                        val_2[1]['percentage_amount_collected'] = 0

                    finals.append((
                        str(val_2[1]['name']),
                        str(locale.format_string('%.0f', val_2[1]['num_transactions'], True)),
                        f"{str(locale.format_string('%.2f', val_2[1]['percentage_transactions'], True))}%",
                        str(locale.format_string('%.2f', float(val_2[1]['amount_pivoted']), True)),
                        f"{str(locale.format_string('%.2f', float(val_2[1]['percentage_amount_collected']), True))}%"
                    ))

                elif key_2 == 3:
                    for key_3, val_3 in val_2.items():
                        if key_3 != 'currency_name':
                            if total_transactions > 0:
                                val_3['percentage_transactions'] = (float(val_3['num_transactions']) / total_transactions) * 100
                            else:
                                val_3['percentage_transactions'] = 0

                            if total_amount2 > 0:
                                val_3['percentage_amount_collected'] = (float(val_3['amount_pivoted']) / total_amount2) * 100
                            else:
                                val_3['percentage_amount_collected'] = 0

                            finals.append((
                                str(val_3['name']),
                                str(locale.format_string('%.0f', val_3['num_transactions'], True)),
                                f"{str(locale.format_string('%.2f', float(val_3['percentage_transactions']), True))}%",
                                str(locale.format_string('%.2f', float(val_3['amount_pivoted']), True)),
                                f"{str(locale.format_string('%.2f', float(val_3['percentage_amount_collected']), True))}%"
                            ))

            # Add exchange rate differential row
            diferencial_cambiario = total_amount2 - total_amount
            porcentaje_diferencial_cambiario = (diferencial_cambiario / total_amount2) * 100 if total_amount2 > 0 else 0
            finals.append((
                'Diferencial Cambiario',
                '0',
                '0,00%',
                str(locale.format_string('%.2f', diferencial_cambiario, True)),
                f"{str(locale.format_string('%.2f', porcentaje_diferencial_cambiario, True))}%"
            ))

            # Sort and prepare the final report
            orden_metodos_de_pago = {
                'Efectivo Bolívares': 1,
                'Efectivo Dólares': 2,
                'Efectivo Pesos': 3,
                'Pago Móvil': 4,
                'Punto de venta Bancamiga': 5,
                'Punto de venta BNC': 6,
                'Punto de venta Bicentenario': 7,
                'Ventag': 8,
                'VenVías': 9,
                'Cobretag': 10,
                'Pago Directo': 11,
                'Pago Directo Bluetooth': 12,
                'Exonerado': 13
            }

            finals_sorted = sorted(finals, key=lambda x: orden_metodos_de_pago.get(x[0], 999))
            finals = [('Tipo de cobro', 'Pagos', 'Porcentaje pagos', 'Monto Bs', 'Porcentaje Monto')] + finals_sorted
            finals.append(('', str(locale.format_string('%d', total_transactions, True)), '', str(locale.format_string('%.2f', total_amount2, True)), ''))

            for j, row in enumerate(finals):
                for datum in row:
                    if j == 0:
                        self.set_font('Arial', 'B', 8)
                        self.set_fill_color(255, 194, 0)
                        self.set_text_color(40, 40, 40)
                    elif j == len(finals) - 1:
                        self.set_font('Arial', 'B', 8)
                        self.set_fill_color(235, 235, 235)
                        self.set_text_color(40, 40, 40)
                    elif j % 2 == 0:
                        self.set_font('Arial', '', 8)
                        self.set_fill_color(255, 255, 255)
                        self.set_text_color(40, 40, 40)
                    elif j % 2 == 1:
                        self.set_font('Arial', '', 8)
                        self.set_fill_color(249, 249, 249)
                        self.set_text_color(40, 40, 40)

                    self.cell(col_width, line_height, datum, border=0, align='C', fill=True)
                self.ln(line_height)

    def subtitle_centered(self, subtitle):
        """
        Centers and formats a subtitle in the report.

        This method sets the font, calculates the width of the subtitle text, centers it horizontally on the page,
        and then draws the subtitle text.

        Parameters:
        - subtitle (str): The subtitle text to be centered and drawn.

        Returns:
        - None
        """
        # Set the font to Arial, bold, size 8
        self.set_font('Arial', 'B', 8)
        
        # Calculate the width of the subtitle text and add some padding
        w = self.get_string_width(subtitle) + 6
        
        # Set the x position to center the subtitle on the page (assuming page width is 210)
        self.set_x((210 - w) / 2)
        
        # Set the line width for the cell border
        self.set_line_width(1)
        
        # Draw the cell with the subtitle text, centered, with no border
        self.cell(w, 20, subtitle, 0, 1, 'C', 0)


@ns.route('/General-PDF-Report-Consolidate')
class GeneralPDFReportConsolidate(Resource):
    @ns.expect(generate_report_general_report_consolidated)
    def post(self):
        """
        Genera un reporte PDF basado en los parámetros enviados.
        """
        try:
            payload = api.payload

            # Verificar si payload es None
            if not payload:
                return {"message": "El cuerpo de la solicitud está vacío o no es válido."}, 400

            # Validar y obtener los parámetros
            start_date = payload.get('start_date')
            end_date = payload.get('end_date')
            general_report_type = payload.get('general_report_type', 'Complete')
            state = payload.get('state', None)
            toll = payload.get('toll', None)
            report_name = payload.get('report_name', 'general_report').replace(' ', '_')
            supervisor_name = payload.get('username')

            if not start_date or not end_date:
                return {"message": "Los campos 'start_date', 'end_date' y 'username' son obligatorios."}, 400

            # Determinar tipo de reporte
            is_complete = general_report_type.lower() == 'complete'

            # Instanciar la clase Report_Generator
            api_key = Report_Generator.authenticate_to_backend()  # Obtener el API key
            if not api_key:
                return {"message": "Error al obtener el API key del backend."}, 500

            report_generator = Report_Generator(api_key=api_key, start_date=start_date, end_date=end_date)

            # Obtener los datos del backend
            report_data = report_generator.fetch_data_from_backend()

            # Verificar si report_data es None o no es un diccionario
            if not report_data:
                return {"message": "Error al obtener los datos del backend."}, 500
            if not isinstance(report_data, dict):
                return {"message": "Los datos obtenidos del backend no son válidos, tipo de datos incorrecto."}, 500

            # Generar el reporte PDF usando los datos obtenidos
            pdf = Report_Generator(api_key=api_key, start_date=start_date, end_date=end_date)

            # Asegúrate de llamar a add_page() para abrir la primera página
            pdf.add_page()
            print("Se logro")

            
            # Llamar a las funciones que generan las secciones del reporte
            print("We are here")
            pdf.general_info()
            print("1")
            pdf.general_rates_by_date()
            print("2")
            pdf.general_rates_by_vehicle()
            print("3")
            pdf.general_rates_by_payment_types()
            print("4")

            # Convertir el PDF a BytesIO
            pdf_data_str = pdf.output(dest='S').encode('latin1')
            print(f"Tipo de datos de pdf_data_str: {type(pdf_data_str)}")
            pdf_data = io.BytesIO(pdf_data_str)
            print("4")

            # Enviar el PDF como respuesta
            return send_file(
                pdf_data,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'{report_name}_{datetime.now().strftime("%Y%m%d%H%M")}.pdf'
            )

        except KeyError as ke:
            return {"message": f"Falta un campo obligatorio: {str(ke)}"}, 400
        except Exception as e:
            return {"message": f"Error interno al generar el reporte: {str(e)}"}, 500





    
# Inicializar la aplicación Flask
if __name__ == "__main__":
    app.run(debug=True, port=8000)

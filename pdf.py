import requests
import io
from datetime import datetime
from flask import Flask, request, jsonify, send_file, Response
from flask_restx import Api, Resource, fields
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
import csv


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

generate_report_general_report_institutional_by_state = api.model('InstitutionalReportPayload', {
    'start_date': fields.String(required=True, description='La fecha de inicio del reporte (formato ISO8601)'),
    'end_date': fields.String(required=True, description='La fecha de fin del reporte (formato ISO8601)'),
    'state': fields.String(required=False, description='El estado a filtrar en el reporte'),
    'toll': fields.String(required=False, description='El peaje a filtrar en el reporte')
})

generate_report_general_report_institutional = api.model('InstitutionalReportPayload', {
    'start_date': fields.String(required=True, description='La fecha de inicio del reporte (formato ISO8601)'),
    'end_date': fields.String(required=True, description='La fecha de fin del reporte (formato ISO8601)'),
    'state': fields.String(required=True, description='El estado a filtrar en el reporte'),
    'toll': fields.String(required=True, description='El peaje a filtrar en el reporte')
})

generate_report_general_report_ministry = api.model('MinistryReportPayload', {
    'start_date': fields.String(required=True, description='La fecha de inicio del reporte (formato ISO8601)'),
    'end_date': fields.String(required=True, description='La fecha de fin del reporte (formato ISO8601)'),
    'state': fields.String(required=False, description='El estado a filtrar en el reporte'),
    'toll': fields.String(required=False, description='El peaje a filtrar en el reporte')
})

ns = api.namespace("reports", description="Report Generation Endpoints")


locale.setlocale(locale.LC_ALL, 'es_VE.UTF-8')
venezuelan_hour = pytz.timezone('America/Caracas')

class Report_Generator(FPDF):
       
    def __init__(self, start_date, end_date,supervisor_info,general_report_type, report_name, state,toll):
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
        self.start_date = start_date
        self.end_date = end_date
        self.format_dot_comma = format_dot_comma
        self.supervisor_info = supervisor_info
        self.state = state
        self.state_name = state
        self.toll = toll
        self.report_name = report_name
        self.general_report_type = general_report_type 
    
    def fetch_data_state(self, state):
        """
        Realiza una solicitud al backend y retorna el JSON de respuesta.

        Returns:
            dict: El JSON de respuesta si la solicitud fue exitosa, None si no lo fue.
        """
        url = "http://127.0.0.1:3001/v1/consolidatedReport"

        data = {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "state": state
        }
        
        
        apikey = "Nvam9tkrV2agWHjXdsdTYvYoMDg2dnUQxZC5wRJMkV5UkmF4fHNHvXfoiTsQejwk7wgj5PVo3DoS"
        
        if not apikey:
            return {"message": "Error al obtener el API key del backend."}, 500
        
        headers = {
            "X-API-Key": apikey
        }

        try:
            response = requests.post(url, json=data, headers=headers)

            if response.status_code == 200:
                print("Datos obtenidos exitosamente del backend (fetch from backend).")
                return response.json()
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

        if self.state:
            data = {
                "start_date": self.start_date,
                "end_date": self.end_date,
                "state": self.state
            }
        else:
            data = {
                "start_date": self.start_date,
                "end_date": self.end_date
            }
            
        print(data)
        
        apikey = "Nvam9tkrV2agWHjXdsdTYvYoMDg2dnUQxZC5wRJMkV5UkmF4fHNHvXfoiTsQejwk7wgj5PVo3DoS"
        
        if not apikey:
            return {"message": "Error al obtener el API key del backend."}, 500
        
        headers = {
            "X-API-Key": apikey
        }
        
        try:
            response = requests.post(url, json=data, headers=headers)

            if response.status_code == 200:
                print("Datos obtenidos exitosamente del backend (fetch from backend).")
                return response.json()
            else:
                print(f"Error al hacer el llamado: {response.status_code}")
                print("Mensaje de error:", response.json())
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error en la solicitud al backend: {e}")
            return None

    def fetch_data_by_toll_from_backend(self):
        """
        Realiza una solicitud por peaje al backend y retorna el JSON de respuesta.

        Returns:
            dict: El JSON de respuesta si la solicitud fue exitosa, None si no lo fue.
        """ 
        url = "http://127.0.0.1:3001/v1/peajeInfo"
        
        data = {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "state": self.state,
            "toll": self.toll
        }
        
        
        apikey = "Nvam9tkrV2agWHjXdsdTYvYoMDg2dnUQxZC5wRJMkV5UkmF4fHNHvXfoiTsQejwk7wgj5PVo3DoS"
        
        if not apikey:
            return {"message": "Error al obtener el API key del backend."}, 500
        
        headers = {
            "X-API-Key": apikey
        }
        
        try:
          response = requests.post(url, json=data, headers=headers)

          if response.status_code == 200:
              print("Datos obtenidos exitosamente del backend (fetch from backend toll).")
              return response.json()
          else:
              print(f"Error al hacer el llamado: {response.status_code}")
              print("Mensaje de error:", response.json())
              return None

        except requests.exceptions.RequestException as e:
            print(f"Error en la solicitud al backend: {e}")
            return None

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
        # Set up the header with the Venpax logo, title, generation date, supervisor information, and date range

        #Set up the Venpax's Image
        self.image('venpax-full-logo.png', 10, 8, 85)
        self.set_font('Arial', 'B', 16)
        self.set_text_color(40, 40, 40)
        self.set_x(100)

        self.cell(0,12, 'Resumen General de Recaudación',align='R',ln=1)
        self.set_font('Arial', 'B', 8.5)
        self.cell(208 - self.get_string_width(f'Generado el {datetime.strftime(datetime.now(venezuelan_hour), "%d/%m/%Y %H:%M:%S")}'), 5, 'Generado el ', 0, 0, 'R')
        self.set_font('Arial', '', 8.5)
        self.cell(0, 5, f' {datetime.strftime(datetime.now(venezuelan_hour), "%d/%m/%Y %H:%M:%S")}', 0, 1, align='R')


        self.set_font('Arial', 'B', 8.5)
        self.cell(213 - self.get_string_width(f'Solicitado por: {self.supervisor_info}'),5, 'Solicitado por: ',align='R')
        self.set_font('Arial', '', 8.5)
        self.cell(0, 5, f'{self.supervisor_info}', 0, 1, align='R')

        self.cell(0,5, f'Del {datetime.strftime(datetime.fromisoformat(self.start_date), "%d/%m/%Y %H:%M:%S")} al {datetime.strftime(datetime.fromisoformat(self.end_date), "%d/%m/%Y %H:%M:%S")}',align='R', ln=1)

        if self.state_name is not None:
            self.set_font('Arial', 'B', 8.5)
            self.cell(203 - self.get_string_width(f'Estado: {self.state_name}'),5, 'Estado:  ',align='R')
            self.set_font('Arial', '', 8.5)
            self.cell(0, 5, f' {self.state_name}', 0, 1, align='R')
        else:
            self.set_font('Arial', 'B', 8.5)
            self.cell(203 - self.get_string_width(f'Estado: Todos'),5, 'Estado:  ',align='R')
            self.set_font('Arial', '', 8.5)
            self.cell(0, 5, f' Todos', 0, 1, align='R')
        if self.toll is not None:
            self.set_font('Arial', 'B', 8.5)
            self.cell(203 - self.get_string_width(f'Peaje:  {self.toll}'),5, 'Peaje:  ',align='R')
            self.set_font('Arial', '', 8.5)
            self.cell(0, 5, f' {self.toll}', 0, 1, align='R')
        else:
            self.set_font('Arial', 'B', 8.5)
            self.cell(203 - self.get_string_width(f'Peaje: Todos'),5, 'Peaje:  ',align='R')
            self.set_font('Arial', '', 8.5)
            self.cell(0, 5, f' {' Todos'}', 0, 1, align='R')
            

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

    def linechart_payments_and_amount_by_date(self,report_data):
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
        # Obtenemos los datos directamente desde el backend
        # Obtenemos los datos por parámetro
        json_data = report_data

        # Verificamos si la respuesta es válida
        if not json_data:
            print("No se pudo obtener los datos del backend. No se generará el PDF.")
            return

        # Procesar los datos obtenidos
        try:
            # Obtenemos la lista 'data', y si no está vacía, tomamos el primer item
            first_data_item = json_data.get("data", [])[0]  # Obtener el primer elemento de la lista "data"
            results = first_data_item.get("data", {}).get("results", {})
            general_data = results.get("fechas", {})
    
            fechas = []
            pagos = []
            amount = []

            # Procesar las filas de datos
            for date, details in general_data.items():
                if details.get("pagos", True):
                    pagos_daily = details.get("pagos", 0)
                    amount_daily = details.get("monto", 0)
                else:
                    pagos_daily = 0
                    amount_daily = 0


                # Append the processed data to the respective lists
                fechas.append(dt.datetime.strptime(date,'%Y-%m-%d').date())
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
        except: 
            print("Error al procesar los datos y generar el gráfico de líneas.")
            return

    def general_info(self, report_data):
        """
        Genera y formatea la sección de información general del reporte.
        """
        # Obtenemos los datos por parámetro
        json_data = report_data

        # Verificamos si la respuesta es válida
        if not json_data:
            print("No se pudo obtener los datos del backend. No se generará el PDF.")
            return
        
        # Procesar los datos obtenidos
        try:
            # Obtenemos la lista 'data', y si no está vacía, tomamos el primer item

            if self.state_name:
              
              # Extraemos los datos relevantes, con valores por defecto en caso de que falten
              first_data_item = json_data.get("data", [])[0]
              results = first_data_item.get("data", {}).get("results", {})
              general_data = results.get("general_data", {})

              total_payments_bs = general_data.get("total_payments_bs", 0)
              total_payments_usd = general_data.get("total_payments_usd", 0)
              vehicles = general_data.get("vehicles", 0)
              
              #Datos de los porcentajes extraidos de los configs
              configs = first_data_item.get("config", {})
              fnt_percentage = configs.get("fnt_percentage", 0)
              state_percentage = configs.get("gob_percentage", 0)
              venpax_percentage = configs.get("venpax_percentage", 0)
              
              #Fondo nacional del transporte
              total_fn_bs = total_payments_bs * fnt_percentage / 100
              total_fn_usd = total_payments_usd * fnt_percentage / 100
              
              #Gobernacion del estado
              total_state_bs = total_payments_bs * state_percentage / 100
              total_state_usd = total_payments_usd * state_percentage / 100
              
              #Venpax
              venpax_bs = total_payments_bs * venpax_percentage / 100
              venpax_usd = total_payments_usd * venpax_percentage / 100
              
              finals = [
                ('Monto Total en Bolívares', 'Monto Total en Dólares', 'Total de Vehículos'),
                (
                    f"Bs. {locale.format_string('%.2f', total_payments_bs, grouping=True)}",
                    f"$ {locale.format_string('%.2f', total_payments_usd, grouping=True)}",
                    f"{locale.format_string('%.0f', vehicles, grouping=True)}"
                ), (f'Fondo Nacional del T. ({fnt_percentage}%)', f'Gob. Estado {self.state_name} ({state_percentage}%)', f'Venpax {self.state_name} ({venpax_percentage}%)'),
                (
                    f"Bs. {locale.format_string('%.2f', total_fn_bs, grouping=True)}",
                    f"Bs. {locale.format_string('%.2f', total_state_bs, grouping=True)}",
                    f"Bs.{locale.format_string('%.0f', venpax_bs, grouping=True)}"
                ),
                (
                    f"${locale.format_string('%.2f', total_fn_usd, grouping=True)}",
                    f"${locale.format_string('%.2f', total_state_usd, grouping=True)}",
                    f"${locale.format_string('%.0f', venpax_usd, grouping=True)}" 
                )
              ]
            
            else:
              
              # Extraer totales por estado en Bs y USD
              total_state = json_data.get("total_por_estado", {})
              state_configs = json_data.get("configs_por_estado", {})

              # Calculo total para Venpax en Bs y USD en cada estado
              venpax_totales = {}
              for state, totales in total_state.items():
                  config = state_configs.get(state, {})
                  venpax_percentage = config.get("venpax_percentage", 0)
                  venpax_totales[state] = {
                      "total_bs_venpax": totales.get("VES", 0) * venpax_percentage / 100,
                      "total_usd_venpax": totales.get("USD", 0) * venpax_percentage / 100
                  }

              # Extraer datos generales
              general_data = json_data["data"][0]["data"]["results"]["general_data"]
              total_payments_bs = general_data.get("total_payments_bs", 0)
              total_payments_usd = general_data.get("total_payments_usd", 0)
              vehicles = general_data.get("vehicles", 0)

              # Renderizar tabla de resultados dinámicamente
              finals = [
                  ('Monto Total en Bolívares', 'Monto Total en Dólares', 'Total de Vehículos'),
                  (
                      f"Bs. {locale.format_string('%.2f', total_payments_bs, grouping=True)}",  # Separador de miles y 2 decimales
                      f"$ {locale.format_string('%.2f', total_payments_usd, grouping=True)}",   # Separador de miles y 2 decimales
                      f"{locale.format_string('%.0f', vehicles, grouping=True)}"               # Separador de miles sin decimales
                  )
              ]

              # Procesar los totales de Venpax para todos los estados
              states = list(venpax_totales.keys())
              vetaesn_heads = tuple(f'Venpax Est. {state}' for state in states)
              venpax_bs_finals = tuple(
                  f"Bs.{locale.format_string('%.2f', venpax_totales[state]['total_bs_venpax'], grouping=True)}"
                  for state in states
              )
              venpax_usd_finals = tuple(
                  f"${locale.format_string('%.2f', venpax_totales[state]['total_usd_venpax'], grouping=True)}"
                  for state in states
              )

              # Añadir los resultados a la tabla
              finals.append(vetaesn_heads)
              finals.append(venpax_bs_finals)
              finals.append(venpax_usd_finals)
 
        except (KeyError, IndexError) as e:
            print(f"Error al procesar los datos del backend: {str(e)}")
            return

        # Formatear los datos y añadirlos al PDF
        for j, row in enumerate(finals):
            for datum in row:
                if j == 0 or j == 2:
                    self.set_font('Arial', 'B', 10)
                    self.set_fill_color(255, 194, 0)
                    self.set_text_color(40, 40, 40)
                elif j == 1 or j == 3:
                    self.set_font('Arial', 'B', 12)
                    self.set_fill_color(255, 255, 255)
                    self.set_text_color(40, 40, 40)
                elif j == 4 or 6:
                    self.set_font('Arial', 'B', 12)
                    self.set_fill_color(255, 255, 255)
                    self.set_text_color(40, 40, 40)

                # Set the cell size and add the data to the report
                # The cell size is calculated based on the number of columns in the row
                self.cell((self.w - 20) / len(row), 11, datum, 0, 0, 'C', fill=True)
            self.ln(11)

        # Resetear el formato de texto al predeterminado
        self.set_font('Arial', '', 12)
 
    def general_rates_by_date(self, report_data):
        """
        Generates a detailed report of access and income by date.
        """
        # Obtener datos por parámetros
        json_data = report_data

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
                    locale.format_string('%.2f', cash_usd, grouping=True),
                    locale.format_string('%.2f', cash_cop, grouping=True),
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
                "-",
                locale.format_string('%.2f', totals["monto_usd"], grouping=True),
                locale.format_string('%.2f', totals["cash_ves"], grouping=True),
                locale.format_string('%.2f', totals["cash_usd"], grouping=True),
                locale.format_string('%.2f', totals["cash_cop"], grouping=True),
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
        for j, row in enumerate(table_data):
            for datum in row:
                if j == 0:  # Primera fila: títulos
                    self.set_font('Arial', 'B', 8)
                    self.set_fill_color(255, 194, 0)
                    self.set_text_color(40, 40, 40)
                elif j == len(table_data) - 1:  # Última fila: totales
                    self.set_font('Arial', 'B', 8)
                    self.set_fill_color(235, 235, 235)
                    self.set_text_color(40, 40, 40)
                elif j % 2 == 0:  # Filas pares
                    self.set_font('Arial', '', 8)
                    self.set_fill_color(255, 255, 255)
                    self.set_text_color(40, 40, 40)
                elif j % 2 == 1:  # Filas impares
                    self.set_font('Arial', '', 8)
                    self.set_fill_color(249, 249, 249)
                    self.set_text_color(40, 40, 40)

                self.cell(col_width, line_height, datum, border=0, align='C', fill=True)
            self.ln(line_height)

    def general_rates_by_vehicle(self, report_data):
        """
        Generates a detailed report of vehicle rates.
        """
        # Obtener datos por parámetros
        json_data = report_data

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
                percentage_amount = (amount / total_amount) * 100 if total_amount else 0
                percentage_ves_cash = (total / total_ves_amount) * 100 if total_ves_amount else 0

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
            for i, datum in enumerate(row):
                if j == 0:  # Encabezados
                    self.set_font('Arial', 'B', 8)
                    self.set_fill_color(255, 194, 0)
                    self.set_text_color(40, 40, 40)
                elif j == len(table_data) - 1:  # Totales
                    self.set_font('Arial', 'B', 8)
                    self.set_fill_color(235, 235, 235)
                    self.set_text_color(40, 40, 40)
                elif j % 2 == 0:  # Filas pares
                    self.set_font('Arial', '', 8)
                    self.set_fill_color(255, 255, 255)
                    self.set_text_color(40, 40, 40)
                else:  # Filas impares
                    self.set_font('Arial', '', 8)
                    self.set_fill_color(249, 249, 249)
                    self.set_text_color(40, 40, 40)

                # Ajustar el ancho de columna
                if i == 0:  # Primera columna
                    self.cell(col_width_first_column, line_height, datum, border=0, align='C', fill=True)
                else:  # Otras columnas
                    self.cell(col_width_others, line_height, datum, border=0, align='C', fill=True)
            self.ln(line_height)

    def general_rates_by_vehicle_by_state(self, report_data):
        """
        Generates a detailed report of vehicle rates.
        """
        # Obtener datos por parámetros
        json_data = report_data

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
            total_amount = total_ves_amount = total_pagos = total_ves_cash =  0
            table_data = [["Tipo de Vehículo", "Cantidad", "% Cantidad", "Monto Bs", "% Monto", "Efvo. Bs"]]

            # Calcular los totales
            for data in general_data.values():
                total_amount += data["cantidad"]
                total_ves_amount += data["monto"]
                total_pagos += data["cantidad"]
                total_ves_cash += data["cash_collected"]["VES"]

            # Añadir los datos a la tabla
            for data in general_data.values():
                amount = data["cantidad"]
                total = data["monto"]
                ves_cash = data["cash_collected"]["VES"]

                # Calcular porcentajes
                percentage_amount = (amount / total_amount) * 100 if total_amount else 0
                percentage_ves_cash = (total / total_ves_amount) * 100 if total_ves_amount else 0

                table_data.append([
                    data["nombre"],
                    locale.format_string('%.0f', amount, grouping=True),
                    f"{locale.format_string('%.2f', percentage_amount, grouping=True)}%",
                    locale.format_string('%.2f', total, grouping=True),
                    f"{locale.format_string('%.2f', percentage_ves_cash, grouping=True)}%",
                    locale.format_string('%.2f', ves_cash, grouping=True),
                ])

            # Agregar fila de totales
            table_data.append([
                "Totales",
                locale.format_string('%.0f', total_pagos, grouping=True),
                "",
                locale.format_string('%.2f', total_ves_amount, grouping=True),
                "",
                locale.format_string('%.2f', total_ves_cash, grouping=True),
            ])
        except (KeyError, IndexError) as e:
            print(f"Error al procesar los datos del backend: {str(e)}")
            return

        # Formatear el informe en PDF
        col_width_first_column = (self.w - 20) * 0.25  # Ajuste de la primera columna (más estrecha)
        col_width_others = (self.w - 20) * 0.15  # Ajuste para que otras columnas ocupen más espacio
        line_height = 6

        subtitle = "Resumen de Tarifas General"
        self.subtitle_centered(subtitle)
        self.set_line_width(0)

        # Calcular el ancho total de la tabla
        total_width = col_width_first_column + (col_width_others * (len(table_data[0]) - 1))

        # Ajustar posición X para centrar la tabla en la página
        x_position = (self.w - total_width) / 2
        self.set_x(x_position)

        # Imprimir la tabla
        for j, row in enumerate(table_data):
            for i, datum in enumerate(row):
                # Configurar estilo según la fila (encabezado, pares, impares)
                if j == 0:  # Encabezados
                    self.set_font('Arial', 'B', 8)
                    self.set_fill_color(255, 194, 0)
                    self.set_text_color(40, 40, 40)
                elif j == len(table_data) - 1:  # Totales
                    self.set_font('Arial', 'B', 8)
                    self.set_fill_color(235, 235, 235)
                    self.set_text_color(40, 40, 40)
                elif j % 2 == 0:  # Filas pares
                    self.set_font('Arial', '', 8)
                    self.set_fill_color(255, 255, 255)
                    self.set_text_color(40, 40, 40)
                else:  # Filas impares
                    self.set_font('Arial', '', 8)
                    self.set_fill_color(249, 249, 249)
                    self.set_text_color(40, 40, 40)

                # Ajustar el ancho de columnas
                if i == 0:  # Primera columna (más ancha)
                    self.cell((self.w - 20) * 0.3, line_height, datum, border=0, align='C', fill=True)
                else:  # Otras columnas (más estrechas)
                    self.cell((self.w - 20) * 0.14, line_height, datum, border=0, align='C', fill=True)
            self.ln(line_height)  # Mover a la siguiente línea

    def general_rates_by_vehicle_2(self, report_data):
        """
        Generates a detailed report of vehicle rates with charts.
        """
        # Obtener datos desde el backend

        date_format = "%Y-%m-%dT%H:%M:%S" 

        try:
            # Calcular la diferencia de días entre las fechas de inicio y fin
            start_date_dt = datetime.strptime(self.start_date, date_format)
            end_date_dt = datetime.strptime(self.end_date, date_format)
        except ValueError as e:
            print(f"Error en el formato de las fechas: {e}")
            return

        delta_days = (end_date_dt - start_date_dt).days
        
        json_data = report_data
        
        if not json_data:
            print("No se pudo obtener los datos del backend. No se generará el PDF.")
            return

        # Procesar los datos obtenidos
        try:
            first_data_item = json_data.get("data", [])[0]
            results = first_data_item.get("data", {}).get("results", {})
            general_data = results.get("tarifas", {})

            if not general_data:
                print("No se pudieron obtener los datos de tarifas. No se generará el reporte.")
                return

            # Inicializar datos
            nombres = []
            cantidades = []
            montos = []

            for tipo, data in general_data.items():
                nombres.append(data["nombre"])
                cantidades.append(data["cantidad"])
                montos.append(data["monto"])

            # Crear DataFrames
            df_1 = pd.DataFrame({'Nombre': nombres, 'Cantidad': cantidades})
            df_2 = pd.DataFrame({'Nombre': nombres, 'Monto': montos})

            # Ordenar datos
            orden_vehiculos = {
                'Vehículo liviano': 1, 'Microbús': 2, 'Autobús': 3,
                'Camión liviano': 4, 'Camión 2 ejes': 5, 'Camión 3 ejes': 6,
                'Camión 4 ejes': 7, 'Camión 5 ejes': 8, 'Camión 6+ ejes': 9,
                'Exonerado General': 10, 'Exonerado Ambulancia': 11,
                'Exonerado Seguridad': 12, 'Exonerado Gobernación': 13,
                'Exonerado PDVSA': 14
            }
            df_1['Orden'] = df_1['Nombre'].map(orden_vehiculos)
            df_1_sorted = df_1.sort_values('Orden')

            df_2['Orden'] = df_2['Nombre'].map(orden_vehiculos)
            df_2_sorted = df_2.sort_values('Orden')

            # Configuramos el tamaño de la figura
            bio = BytesIO()   

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

            # Añadir etiquetas de porcentaje encima de cada barra
            for index, value in enumerate(df_1_sorted['Cantidad']):
                ax[0, 0].text(df_1_sorted['Cantidad'].max() * 0.05, index, f'Total = {str(locale.format_string("%.f", value, True))}', va='center', fontsize=10, color='black', weight='bold')

            for index, value in enumerate(df_2_sorted['Monto']):
                ax[0, 1].text(df_2_sorted['Monto'].max() * 0.05, index, f'Bs. {str(locale.format_string("%.2f", value, True))}', va='center', fontsize=10, color='black', weight='bold')

            ax[0, 0].set_xlim(0, df_1_sorted['Cantidad'].max() * 1.2)
            ax[0, 1].set_xlim(0, df_2_sorted['Monto'].max() * 1.2)

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
       
            df_3 = pd.DataFrame({'Nombre': nombres, 'Cantidad': cantidades})
            df_4 = pd.DataFrame({'Nombre': nombres, 'Monto': montos})

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

        except Exception as e:
            print(f"Error procesando los datos: {e}")

    def general_rates_by_payment_types(self, report_data):
        """
        Generates a detailed report of payment methods and their respective rates.
        """
        # Título del reporte
        subtitle = "Resumen de Métodos de Pago General"

        # Obtener datos por parámetros
        json_data = report_data
        
        if not json_data:
            print("No se pudo obtener los datos del backend. No se generará el PDF.")
            return

        try:
            # Verificar si la estructura de los datos es válida
            data = json_data.get("data", [])
            if not data:
                print("No se encontraron datos en la respuesta del backend.")
                return

            first_data_item = data[0]  # Obtener el primer elemento de la lista de datos
            results = first_data_item.get("data", {}).get("results", {})
            general_data = results.get("metodos_pago", {})

            if not general_data:
                print("No se pudieron obtener los datos de métodos de pago. No se generará el reporte.")
                return

            # Inicializar variables para los totales
            total_num_transactions = 0
            total_ves_amount = 0
            
            # Lista para almacenar los datos de la tabla
            table_data = [["Método de Pago", "N° Transacciones", "% Transacciones", "Monto Bs", "% Monto"]]

            # Generar filas para cada método de pago en el orden definido
            
            for key, payment_methods in general_data.items():
              for inner_key, data in payment_methods.items():
                  if isinstance(data, dict):
                    if data.get("amount",0) != 0:
                        num_transactions = data.get("num_transactions",0)
                        total = data.get("amount_pivoted",0)
                        payment_name = data.get("name", "") 
                        percentage_transactions = (
                        (num_transactions / total_num_transactions) * 100 if total_num_transactions else 0)
                        percentage_amount_collected = ((total / total_ves_amount) * 100 if total_ves_amount else 0)

                        # Agregar fila a la tabla
                        table_data.append(
                            [
                                payment_name,
                                locale.format_string('%.0f', num_transactions, grouping=True),
                                f"{locale.format_string('%.2f', percentage_transactions, grouping=True)}%",
                                locale.format_string('%.2f', total, grouping=True),
                                f"{locale.format_string('%.2f', percentage_amount_collected, grouping=True)}%",
                            ]
                        )
                        
                        # Totales
                        total_num_transactions += data.get("num_transactions", 0)
                        total_ves_amount += data.get("amount_pivoted", 0)
   
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
        col_width = (self.w - 20) / 5

        self.subtitle_centered(subtitle)
        self.set_line_width(0)

        for j, row in enumerate(table_data):
            for i, datum in enumerate(row):
                # Estilos por fila
                if j == 0:  # Encabezados
                    self.set_font('Arial', 'B', 8)
                    self.set_fill_color(255, 194, 0)
                    self.set_text_color(40, 40, 40)
                elif j == len(table_data) - 1:  # Totales
                    self.set_font('Arial', 'B', 8)
                    self.set_fill_color(235, 235, 235)
                    self.set_text_color(40, 40, 40)
                elif j % 2 == 0:  # Filas pares
                    self.set_font('Arial', '', 8)
                    self.set_fill_color(255, 255, 255)
                    self.set_text_color(40, 40, 40)
                else:  # Filas impares
                    self.set_font('Arial', '', 8)
                    self.set_fill_color(249, 249, 249)
                    self.set_text_color(40, 40, 40)

                self.cell(col_width, line_height, datum, border=0, align='C', fill=True)
            self.ln(line_height)

    def general_rates_by_payments_types_2(self, report_data):
        """
        Generates a detailed report of payment methods and their respective rates.
        """
        # Obtener datos por parámetros
        json_data = report_data

        
        if not json_data:
            print("No se pudo obtener los datos del backend. No se generará el PDF.")
            return

        try:
            # Verificar si la estructura de los datos es válida
            data = json_data.get("data", [])
            if not data:
                print("No se encontraron datos en la respuesta del backend.")
                return

            first_data_item = data[0]  # Obtener el primer elemento de la lista de datos
            results = first_data_item.get("data", {}).get("results", {})
            general_data = results.get("metodos_pago", {})

            if not general_data:
                print("No se pudieron obtener los datos de métodos de pago. No se generará el reporte.")
                return
            
            # Preparar datos para el gráfico
            methods = []
            amounts = []
            total_amounts = []
            transactions = []
            percentage_transactions = []
            percentage_amount = []
            name = []
            #Aqui itero para los metodos de pago
            for x,y in general_data.items():
                for w,z in y.items():
                    if isinstance(z, dict):
                        if z["name"] not in methods:
                            methods.append(z["name"])
                            amounts.append(z["num_transactions"])
                            total_amounts.append(z["amount_pivoted"])
                            transactions.append(z["num_transactions"])
                            percentage_transactions.append(z["percentage_transactions"])
            print(len(methods))
            #Aqui itero para las monedas y sus stats
            for x, y in general_data.items():
                name.append(y["currency_name"])
                percentage_amount.append(y["percentage_amount_collected"])

            
            df_1 = pd.DataFrame({'Nombre': methods, 'Cantidad': amounts})
            df_2 = pd.DataFrame({'Nombre': methods, 'Monto': total_amounts})
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
            fig, ax = plt.subplots(2, 2, figsize=(16, 17))

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

            # Set tick positions first, then set the labels
            ax[0, 0].set_xticks(ax[0, 0].get_xticks())  # Ensures the correct number of ticks are set
            ax[0, 0].set_xticklabels(ax[0, 0].get_xticklabels(), rotation=45, ha='center')

            ax[0, 1].set_xticks(ax[0, 1].get_xticks())  # Ensures the correct number of ticks are set
            ax[0, 1].set_xticklabels(ax[0, 1].get_xticklabels(), rotation=45, ha='center')


            # Agregar títulos a cada gráfica
            ax[0, 0].set_title('Cantidad de Pagos por Método de Pago', fontsize=15, pad=20, loc='center', weight='bold')
            ax[0, 1].set_title('Monto de Pagos por Método de Pago', fontsize=15, pad=20, loc='center', weight='bold')


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
            df_3 = pd.DataFrame({'Nombre': methods, 'Cantidad': amounts})
            df_4 = pd.DataFrame({'Nombre': name, 'Cantidad': percentage_amount})
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

        
        except Exception as e:
            return {"message": f"Error interno al generar el reporte (manejo de métodos de pago): {str(e)}"}, 500
          
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

    def general_info_institutional_by_state(self,report_data):
        """
        Genera y formatea la sección de información general del reporte por estado.
        """
        # Obtenemos los datos por parámetro
        json_data = report_data

        # Verificamos si la respuesta es válida
        if not json_data:
            print("No se pudo obtener los datos del backend. No se generará el PDF.")
            return

        
        # Procesar los datos obtenidos
        try:
            # Obtenemos la lista 'data', y si no está vacía, tomamos el primer item

            if self.state_name:
              
              # Extraemos los datos relevantes, con valores por defecto en caso de que falten
              first_data_item = json_data.get("data", [])[0]
              results = first_data_item.get("data", {}).get("results", {})
              general_data = results.get("general_data", {})

              # Obtengo los bs y vehiculos 
              total_payments_bs = general_data.get("total_payments_bs", 0)
              vehicles = general_data.get("vehicles", 0)
              
              #Datos de los porcentajes extraidos de los configs
              configs = first_data_item.get("config", {})
              fnt_percentage = configs.get("fnt_percentage", 0)
              state_percentage = configs.get("gob_percentage", 0)
              venpax_percentage = configs.get("venpax_percentage", 0)
              
              #Fondo nacional del transporte
              total_fn_bs = total_payments_bs * fnt_percentage / 100
              
              #Gobernacion del estado
              total_state_bs = total_payments_bs * state_percentage / 100
              
              #Venpax
              venpax_bs = total_payments_bs * venpax_percentage / 100
              
              finals = [
                ('Monto Total en Bolívares', 'Total de Vehículos'),
                (
                    f"Bs. {locale.format_string('%.2f', total_payments_bs, grouping=True)}",
                    f"{locale.format_string('%.0f', vehicles, grouping=True)}"
                ), (f'Fondo Nacional del T. ({fnt_percentage}%)', f'Gob. Estado {self.state_name} ({state_percentage}%)', f'Venpax {self.state_name} ({venpax_percentage}%)'),
                (
                    f"Bs. {locale.format_string('%.2f', total_fn_bs, grouping=True)}",
                    f"Bs. {locale.format_string('%.2f', total_state_bs, grouping=True)}",
                    f"Bs.{locale.format_string('%.0f', venpax_bs, grouping=True)}"
                ),
              ]
            
            else:
              
              # Extraer totales por estado en Bs y USD
              total_state = json_data.get("total_por_estado", {})
              

              # Extraer datos generales
              general_data = json_data["data"][0]["data"]["results"]["general_data"]
              total_payments_bs = general_data.get("total_payments_bs", 0)
              vehicles = general_data.get("vehicles", 0)

              # Renderizar tabla de resultados dinámicamente
              finals = [
                  ('Monto Total en Bolívares', 'Monto Total en Dólares', 'Total de Vehículos'),
                  (
                      f"Bs. {locale.format_string('%.2f', total_payments_bs, grouping=True)}",  # Separador de miles y 2 decimales
                  )
              ]

        except (KeyError, IndexError) as e:
            print(f"Error al procesar los datos del backend: {str(e)}")
            return

        # Formatear los datos y añadirlos al PDF
        for j, row in enumerate(finals):
            for datum in row:
                if j == 0 or j == 2:
                    self.set_font('Arial', 'B', 10)
                    self.set_fill_color(255, 194, 0)
                    self.set_text_color(40, 40, 40)
                elif j == 1 or j == 3:
                    self.set_font('Arial', 'B', 12)
                    self.set_fill_color(255, 255, 255)
                    self.set_text_color(40, 40, 40)
                elif j == 4 or 6:
                    self.set_font('Arial', 'B', 12)
                    self.set_fill_color(255, 255, 255)
                    self.set_text_color(40, 40, 40)

                # Set the cell size and add the data to the report
                # The cell size is calculated based on the number of columns in the row
                self.cell((self.w - 20) / len(row), 11, datum, 0, 0, 'C', fill=True)
            self.ln(11)

        # Resetear el formato de texto al predeterminado
        self.set_font('Arial', '', 12)

    def general_info_institutional_by_toll(self,report_data):
        """
        Genera y formatea la sección de información general del reporte por peaje.
        """
        # Obtenemos los datos por parámetro
        json_data = report_data

        # Verificamos si la respuesta es válida
        if not json_data:
            print("No se pudo obtener los datos del backend. No se generará el PDF.")
            return

        try:
            # Extraemos los datos relevantes, con valores por defecto en caso de que falten
            datas = json_data.get("data", [])

            for data in datas:
                for key,value in data.items():
                    if self.toll == value:
                        print("Entro")
                        configs = data.get("config", {})
                        results = data.get("data", {}).get("results", {})
                        general_data = results.get("general_data", {})

            
            # Obtengo los bs y vehiculos 
            total_payments_bs = general_data.get("total_payments_bs", 0)
            vehicles = general_data.get("vehicles", 0) 

            fnt_percentage = configs.get("fnt_percentage", 0)
            state_percentage = configs.get("gob_percentage", 0)
            venpax_percentage = configs.get("venpax_percentage", 0)
            
            #Fondo nacional del transporte
            total_fn_bs = total_payments_bs * fnt_percentage / 100
            
            #Gobernacion del estado
            total_state_bs = total_payments_bs * state_percentage / 100
            
            #Venpax
            venpax_bs = total_payments_bs * venpax_percentage / 100
            
            finals = [
            ('Monto Total en Bolívares', 'Total de Vehículos'),
            (
                f"Bs. {locale.format_string('%.2f', total_payments_bs, grouping=True)}",
                f"{locale.format_string('%.0f', vehicles, grouping=True)}"
            ), (f'Fondo Nacional del T. ({fnt_percentage}%)', f'Gob. Estado {self.state_name} ({state_percentage}%)', f'Venpax {self.state_name} ({venpax_percentage}%)'),
            (
                f"Bs. {locale.format_string('%.2f', total_fn_bs, grouping=True)}",
                f"Bs. {locale.format_string('%.2f', total_state_bs, grouping=True)}",
                f"Bs.{locale.format_string('%.0f', venpax_bs, grouping=True)}"
            ),
            ]

        except (KeyError, IndexError) as e:
            print(f"Error al procesar los datos del backend: {str(e)}")
            return

        # Formatear los datos y añadirlos al PDF
        for j, row in enumerate(finals):
            for datum in row:
                if j == 0 or j == 2:
                    self.set_font('Arial', 'B', 10)
                    self.set_fill_color(255, 194, 0)
                    self.set_text_color(40, 40, 40)
                elif j == 1 or j == 3:
                    self.set_font('Arial', 'B', 12)
                    self.set_fill_color(255, 255, 255)
                    self.set_text_color(40, 40, 40)
                elif j == 4 or 6:
                    self.set_font('Arial', 'B', 12)
                    self.set_fill_color(255, 255, 255)
                    self.set_text_color(40, 40, 40)

                # Set the cell size and add the data to the report
                # The cell size is calculated based on the number of columns in the row
                self.cell((self.w - 20) / len(row), 11, datum, 0, 0, 'C', fill=True)
            self.ln(11)

        # Resetear el formato de texto al predeterminado
        self.set_font('Arial', '', 12)

    def general_info_csv(self, report_data):
        """
        Procesa los datos y genera un archivo CSV con una tabla que muestra tarifas generales de vehículos.
        """
        try:
            # Extraer datos del JSON
            first_data_item = report_data.get("data", [])[0]
            results = first_data_item.get("data", {}).get("results", {})
            general_data = results.get("tarifas", {})

            if not general_data:
                raise ValueError("No se encontraron datos de tarifas.")

            # Inicializar totales
            total_amount = total_ves_amount = total_pagos = total_ves_cash = 0
            csv_data = [["Tipo de Vehículo", "Cantidad", "% Cantidad", "Monto Bs", "% Monto", "Efvo. Bs"]]

            # Calcular totales
            for data in general_data.values():
                total_amount += data["cantidad"]
                total_ves_amount += data["monto"]
                total_pagos += data["cantidad"]
                total_ves_cash += data["cash_collected"]["VES"]

            # Añadir datos al CSV
            for data in general_data.values():
                amount = data["cantidad"]
                total = data["monto"]
                ves_cash = data["cash_collected"]["VES"]

                # Calcular porcentajes
                percentage_amount = (amount / total_amount) * 100 if total_amount else 0
                percentage_ves_cash = (total / total_ves_amount) * 100 if total_ves_amount else 0

                csv_data.append([
                    data["nombre"],
                    locale.format_string('%.0f', amount, grouping=True),
                    f"{locale.format_string('%.2f', percentage_amount, grouping=True)}%",
                    locale.format_string('%.2f', total, grouping=True),
                    f"{locale.format_string('%.2f', percentage_ves_cash, grouping=True)}%",
                    locale.format_string('%.2f', ves_cash, grouping=True),
                ])

            # Fila de totales
            csv_data.append([
                "Totales",
                locale.format_string('%.0f', total_pagos, grouping=True),
                "",
                locale.format_string('%.2f', total_ves_amount, grouping=True),
                "",
                locale.format_string('%.2f', total_ves_cash, grouping=True),
            ])

            # Generar CSV en memoria
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Título para la primera tabla
            writer.writerow(["Reporte de Tarifas Generales de Vehículos"])
            writer.writerow([])  # Línea en blanco entre el título y la tabla
            writer.writerows(csv_data)
            output.write("\n")  # Añadir espacio antes de la siguiente tabla

            output.seek(0)
            return output.getvalue()

        except (KeyError, IndexError, ValueError) as e:
            raise ValueError(f"Error al procesar los datos: {str(e)}")
        
    def general_rates_by_vehicle_state_csv(self, report_data):
        """
        Genera un archivo CSV con la información de tarifas de vehículos agrupadas por estado.
        """
        try:
            # Obtener datos por parámetros
            json_data = report_data

            if not json_data:
                raise ValueError("No se pudo obtener los datos del backend. No se generará el CSV.")

            # Procesar los datos obtenidos
            first_data_item = json_data.get("data", [])[0]  # Obtener el primer elemento de la lista "data"
            results = first_data_item.get("data", {}).get("results", {})
            general_data = results.get("tarifas", {})

            if not general_data:
                raise ValueError("No se pudieron obtener los datos de tarifas. No se generará el reporte.")

            # Inicializar totales y datos de la tabla
            total_amount = total_ves_amount = total_pagos = total_ves_cash = 0
            table_data = [["Tipo de Vehículo", "Cantidad", "% Cantidad", "Monto Bs", "% Monto", "Efvo. Bs"]]

            # Calcular los totales
            for data in general_data.values():
                total_amount += data["cantidad"]
                total_ves_amount += data["monto"]
                total_pagos += data["cantidad"]
                total_ves_cash += data["cash_collected"]["VES"]

            # Añadir los datos a la tabla
            for data in general_data.values():
                amount = data["cantidad"]
                total = data["monto"]
                ves_cash = data["cash_collected"]["VES"]

                # Calcular porcentajes
                percentage_amount = (amount / total_amount) * 100 if total_amount else 0
                percentage_ves_cash = (total / total_ves_amount) * 100 if total_ves_amount else 0

                table_data.append([
                    data["nombre"],
                    locale.format_string('%.0f', amount, grouping=True),
                    f"{locale.format_string('%.2f', percentage_amount, grouping=True)}%",
                    locale.format_string('%.2f', total, grouping=True),
                    f"{locale.format_string('%.2f', percentage_ves_cash, grouping=True)}%",
                    locale.format_string('%.2f', ves_cash, grouping=True),
                ])

            # Agregar fila de totales
            table_data.append([
                "Totales",
                locale.format_string('%.0f', total_pagos, grouping=True),
                "",
                locale.format_string('%.2f', total_ves_amount, grouping=True),
                "",
                locale.format_string('%.2f', total_ves_cash, grouping=True),
            ])

            # Crear un buffer para el CSV
            output = io.StringIO()
            csv_writer = csv.writer(output)

            # Título para la segunda tabla
            csv_writer.writerow(["Reporte de Tarifas de Vehículos por Estado"])
            csv_writer.writerow([])  # Línea en blanco entre el título y la tabla

            # Escribir los datos de la tabla en el CSV
            csv_writer.writerows(table_data)
            output.seek(0)

            return output.getvalue()

        except (KeyError, IndexError) as e:
            raise ValueError(f"Error al procesar los datos: {str(e)}")

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
            if general_report_type == 'Complete':

                pdf = Report_Generator(start_date=start_date, end_date=end_date, supervisor_info=supervisor_name,
                                       general_report_type=general_report_type, report_name=report_name, state=state,toll=toll)

                # Obtener los datos del backend
                report_data = pdf.fetch_data_from_backend()

                # Verificar si report_data es None o no es un diccionario
                if not report_data:
                    return {"message": "Error al obtener los datos del backend."}, 500
                if not isinstance(report_data, dict):
                    return {"message": "Los datos obtenidos del backend no son válidos, tipo de datos incorrecto."}, 500

                # Asegúrate de llamar a add_page() para abrir la primera página
                pdf.add_page()
                
                start_date = datetime.fromisoformat(start_date)
                end_date= datetime.fromisoformat(end_date)
                difference_days = end_date - start_date

                if difference_days > timedelta(days=3):
                    # Llamar a las funciones que generan las secciones del reporte
                    pdf.general_info(report_data)
                    pdf.linechart_payments_and_amount_by_date(report_data)
                    pdf.add_page()
                    pdf.general_rates_by_vehicle_2(report_data)
                    pdf.add_page()
                    pdf.general_rates_by_payments_types_2(report_data)
                    pdf.general_rates_by_date(report_data)
                    pdf.general_rates_by_vehicle(report_data)
                    pdf.general_rates_by_payment_types(report_data)

                    # Convertir el PDF a BytesIO
                    pdf_data_str = pdf.output(dest='S').encode('latin1')
                    pdf_data = io.BytesIO(pdf_data_str)

                    # Enviar el PDF como respuesta
                    return send_file(
                        pdf_data,
                        mimetype='application/pdf',
                        as_attachment=True,
                        download_name=f'{report_name}_{datetime.now().strftime("%Y%m%d%H%M")}.pdf'
                    )
                else:
                    # Llamar a las funciones que generan las secciones del reporte
                    pdf.general_info(report_data)
                    # pdf.general_rates_by_vehicle_2(report_data)
                    # pdf.general_rates_by_payments_types_2(report_data)
                    # pdf.general_rates_by_date(report_data)
                    # pdf.general_rates_by_vehicle(report_data)
                    # pdf.general_rates_by_payment_types(report_data)

                    # Convertir el PDF a BytesIO
                    pdf_data_str = pdf.output(dest='S').encode('latin1')
                    pdf_data = io.BytesIO(pdf_data_str)

                    # Enviar el PDF como respuesta
                    return send_file(
                        pdf_data,
                        mimetype='application/pdf',
                        as_attachment=True,
                        download_name=f'{report_name}_{datetime.now().strftime("%Y%m%d%H%M")}.pdf'
                    )
 
            else:

                pdf = Report_Generator(start_date=start_date, end_date=end_date, supervisor_info=supervisor_name,
                                       general_report_type=general_report_type, report_name=report_name, state=state,toll=toll)

                # Obtener los datos del backend
                report_data = pdf.fetch_data_from_backend()

                # Verificar si report_data es None o no es un diccionario
                if not report_data:
                    return {"message": "Error al obtener los datos del backend."}, 500
                if not isinstance(report_data, dict):
                    return {"message": "Los datos obtenidos del backend no son válidos, tipo de datos incorrecto."}, 500

                # Asegúrate de llamar a add_page() para abrir la primera página
                pdf.add_page()
                
                # Llamar a las funciones que generan las secciones del reporte
                pdf.general_info(report_data)
                pdf.general_rates_by_date(report_data)
                pdf.general_rates_by_vehicle(report_data)
                pdf.general_rates_by_payment_types(report_data)

                # Convertir el PDF a BytesIO
                pdf_data_str = pdf.output(dest='S').encode('latin1')
                pdf_data = io.BytesIO(pdf_data_str)

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
   
@ns.route('/General-PDF-Report-Institutional-by-state')
class General_PDF_Report_Institutional_By_State(Resource):
    @ns.expect(generate_report_general_report_institutional_by_state)
    def post(self):
        """ Generar el reporte para el usuario Institucional """
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

        #Genero el reporte 
        pdf = Report_Generator(start_date=start_date, end_date=end_date, supervisor_info=supervisor_name,
        general_report_type=general_report_type, report_name=report_name, state=state,toll=toll)

        if state and not toll:
            start_date = datetime.fromisoformat(start_date)
            end_date= datetime.fromisoformat(end_date)
            difference_days = end_date - start_date
            # Obtener los datos del backend
            report_data = pdf.fetch_data_from_backend()
             # Verificar si report_data es None o no es un diccionario
            if not report_data:
                return {"message": "Error al obtener los datos del backend."}, 500
            if not isinstance(report_data, dict):
                return {"message": "Los datos obtenidos del backend no son válidos, tipo de datos incorrecto."}, 500

            if difference_days > timedelta(days=3):
                pdf.add_page()
                pdf.general_info_institutional_by_state(report_data)
                pdf.linechart_payments_and_amount_by_date(report_data)
                pdf.general_rates_by_vehicle_by_state(report_data)
                pdf.add_page()
                pdf.general_rates_by_vehicle_2(report_data)
            else:
                pdf.add_page()
                pdf.general_info_institutional_by_state(report_data)
                pdf.general_rates_by_vehicle_by_state(report_data)
                pdf.add_page()
                pdf.general_rates_by_vehicle_2(report_data)

        else:
            start_date = datetime.fromisoformat(start_date)
            end_date= datetime.fromisoformat(end_date)
            difference_days = end_date - start_date

            report_data = pdf.fetch_data_by_toll_from_backend()
            # Verificar si report_data es None o no es un diccionario
            if not report_data:
                return {"message": "Error al obtener los datos del backend."}, 500
            if not isinstance(report_data, dict):
                return {"message": "Los datos obtenidos del backend no son válidos, tipo de datos incorrecto."}, 500
            if difference_days > timedelta(days=3):
                pdf.add_page()
                pdf.general_info_institutional_by_toll(report_data)
                pdf.linechart_payments_and_amount_by_date(report_data)
                pdf.general_rates_by_vehicle_by_state(report_data)
                pdf.add_page()
                pdf.general_rates_by_vehicle_2(report_data)
            else:
                pdf.add_page()
                pdf.general_info_institutional_by_toll(report_data)
                pdf.general_rates_by_vehicle_by_state(report_data)
                pdf.add_page()
                pdf.general_rates_by_vehicle_2(report_data)
        # Convertir el PDF a BytesIO
        pdf_data_str = pdf.output(dest='S').encode('latin1')
        pdf_data = io.BytesIO(pdf_data_str)

        # Enviar el PDF como respuesta
        return send_file(
            pdf_data,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{report_name}_{datetime.now().strftime("%Y%m%d%H%M")}.pdf'
        )



@ns.route('/General-PDF-Report-ministry')
class General_PDF_Report_Ministry(Resource):
    @ns.expect(generate_report_general_report_ministry)
    def post(self):
        """ Generar el reporte por peaje para usuario de ministerio """
        # Verificar si payload es None
        payload = api.payload         
                
        if not payload:
            return {"message": "El cuerpo de la solicitud está vacío o no es válido."}, 400
          
        # Validar y obtener los parámetros
        start_date = payload.get('start_date')
        end_date = payload.get('end_date')
        state = payload.get('state', None)
        toll = payload.get('toll', None)
        report_name = payload.get('report_name', 'general_report').replace(' ', '_')
        
        if not (start_date or end_date or state or toll):
          return {"message": "Todos los campos son obligatorios."}, 400
        
        # Generar el reporte 
        pdf = Report_Generator(start_date=start_date, end_date=end_date, supervisor_info=None,
            general_report_type=None, report_name=report_name, state=state,toll=toll)
        
        pdf.add_page()
        
        if toll:
          
          # Obtener los datos del backend
          report_data = pdf.fetch_data_by_toll_from_backend()
          
          # Llamar a las funciones que generan las secciones del reporte
          pdf.general_info(report_data)
          pdf.linechart_payments_and_amount_by_date(report_data)
          pdf.add_page()
          pdf.general_rates_by_vehicle_2(report_data)
          
          # Convertir el PDF a BytesIO
          pdf_data_str = pdf.output(dest='S').encode('latin1')
          pdf_data = io.BytesIO(pdf_data_str)

          # Enviar el PDF como respuesta
          return send_file(
              pdf_data,
              mimetype='application/pdf',
              as_attachment=True,
              download_name=f'{report_name}_{datetime.now().strftime("%Y%m%d%H%M")}.pdf'
          ) 
          
        else:
        
          # Obtener los datos del backend
          report_data = pdf.fetch_data_from_backend()
          
          # Verificar si report_data es None o no es un diccionario
          if not report_data:
              return {"message": "Error al obtener los datos del backend."}, 500
          if not isinstance(report_data, dict):
              return {"message": "Los datos obtenidos del backend no son válidos, tipo de datos incorrecto."}, 500
            
          start_date = datetime.fromisoformat(start_date)
          end_date= datetime.fromisoformat(end_date)
          difference_days = end_date - start_date

          if difference_days > timedelta(days=3):
            
              # Llamar a las funciones que generan las secciones del reporte
              pdf.general_info(report_data)
              pdf.linechart_payments_and_amount_by_date(report_data)
              pdf.add_page()
              pdf.general_rates_by_vehicle_2(report_data)
              
              # Convertir el PDF a BytesIO
              pdf_data_str = pdf.output(dest='S').encode('latin1')
              pdf_data = io.BytesIO(pdf_data_str)

              # Enviar el PDF como respuesta
              return send_file(
                  pdf_data,
                  mimetype='application/pdf',
                  as_attachment=True,
                  download_name=f'{report_name}_{datetime.now().strftime("%Y%m%d%H%M")}.pdf'
              ) 
          
          else:
            
              # Llamar a las funciones que generan las secciones del reporte
              pdf.general_info(report_data)
              pdf.add_page()
              pdf.general_rates_by_vehicle_2(report_data)
              
              # Convertir el PDF a BytesIO
              pdf_data_str = pdf.output(dest='S').encode('latin1')
              pdf_data = io.BytesIO(pdf_data_str)

              # Enviar el PDF como respuesta
              return send_file(
                  pdf_data,
                  mimetype='application/pdf',
                  as_attachment=True,
                  download_name=f'{report_name}_{datetime.now().strftime("%Y%m%d%H%M")}.pdf'
              ) 

#Endpoint para generar el CSV
@ns.route('/General-CSV-Report')
class GeneralCSVReport(Resource):
    @ns.expect(generate_report_general_report_consolidated)
    def post(self):
        payload = request.json

        if not payload:
            return {"message": "El cuerpo de la solicitud está vacío o no es válido."}, 400

        try:
            # Crear instancia del generador de reportes
            pdf = Report_Generator(
                start_date=payload['start_date'],
                end_date=payload['end_date'],
                supervisor_info=None,
                general_report_type=None,
                report_name=payload.get('report_name', 'general_report').replace(' ', '_'),
                state=payload.get('state', None),
                toll=payload.get('toll', None)
            )

            # Obtener los datos del backend
            report_data = pdf.fetch_data_from_backend()

            if not report_data:
                return {"message": "Error al obtener los datos del backend."}, 500

            # Generar las dos secciones del CSV
            general_info_csv = pdf.general_info_csv(report_data)
            rates_by_state_csv = pdf.general_rates_by_vehicle_state_csv(report_data)

            # Combinar los dos reportes en un solo archivo CSV
            combined_csv_content = general_info_csv + "\n\n" + rates_by_state_csv

            # Configurar la respuesta HTTP para descargar el CSV
            response = Response(combined_csv_content, mimetype='text/csv')
            response.headers['Content-Disposition'] = 'attachment; filename=combined_rates_report.csv'
            return response
        

        except Exception as e:
            return {"message": f"Ocurrió un error al procesar la solicitud: {str(e)}"}, 500


# Inicializar la aplicación Flask
if __name__ == "__main__":
    app.run(debug=True, port=8000)
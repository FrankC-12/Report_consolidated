import requests
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from datetime import datetime
import locale
from dotenv import load_dotenv
import os

# Me traigo el api key del .env
load_dotenv()
API_KEY = os.getenv('API_KEY')
# Llamada a la función con formato correcto de fechas
api_key = API_KEY
start_date = "2024-12-09T00:00:00"  # Con formato requerido
end_date = "2024-12-11T00:00:00"   
def fetch_data_from_backend(api_key, start_date, end_date):
    """
    Realiza una solicitud al backend y retorna el JSON de respuesta.

    Args:
        api_key (str): La clave de API para autenticar la solicitud.
        start_date (str): Fecha de inicio en formato YYYY-MM-DDTHH:MM:SS.
        end_date (str): Fecha de fin en formato YYYY-MM-DDTHH:MM:SS.

    Returns:
        dict: El JSON de respuesta si la solicitud fue exitosa, None si no lo fue.
    """
    # URL del backend
    url = "http://127.0.0.1:3001/v1/consolidatedReport"

    # Datos de la solicitud
    data = {
        "start_date": start_date,  # Formato con tiempo
        "end_date": end_date
    }

    # Headers con la API Key
    headers = {
        "X-API-Key": api_key  # Cambia el nombre si el backend usa otro campo para la API Key
    }

    try:
        # Hacer la solicitud POST al backend
        response = requests.post(url, json=data, headers=headers)

        # Verificar si la solicitud fue exitosa
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


def general_info(api_key, start_date, end_date):
    """
    Obtiene datos desde el backend y genera un PDF con la información general.

    Args:
        api_key (str): La clave de API para autenticar la solicitud.
        start_date (str): Fecha de inicio en formato YYYY-MM-DDTHH:MM:SS.
        end_date (str): Fecha de fin en formato YYYY-MM-DDTHH:MM:SS.

    Returns:
        None
    """
    # Llamar a la función para obtener los datos del backend
    json_data = fetch_data_from_backend(api_key, start_date, end_date)
    if not json_data:
        print("No se pudo obtener los datos del backend. No se generará el PDF.")
        return

    # Procesar los datos obtenidos (acceder al primer elemento de la lista)
    first_data_item = json_data.get("data", [])[0]  # Obtener el primer elemento de la lista "data"
    results = first_data_item.get("data", {}).get("results", {})
    general_data = results.get("general_data", {})  # Cambiar a la clave relevante en el JSON

    # Extraer datos relevantes
    total_payments_bs = general_data.get("total_payments_bs", 0)
    total_payments_usd = general_data.get("total_payments_usd", 0)
    vehicles = general_data.get("vehicles", 0)

    # Preparar los datos para la tabla
    table_data = [
        ['Monto Total en Bolívares', 'Monto Total en Dólares', 'Total de Vehículos'],
        [f"Bs. {total_payments_bs:,.2f}", f"${total_payments_usd:,.2f}", f"{vehicles:,}"]
    ]

    # Crear un archivo PDF
    pdf_file = "general_info_report.pdf"
    pdf = SimpleDocTemplate(pdf_file, pagesize=letter)

    # Estilos
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.alignment = 1

    # Agregar título y datos
    elements = []
    elements.append(Paragraph("Reporte General de Información", title_style))
    elements.append(Spacer(1, 20))

    # Crear la tabla
    table = Table(table_data, colWidths=[200, 200, 150])

    # Estilo de la tabla
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.yellow),  # Cabecera
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),   # Color del texto de la cabecera
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Fuente de la cabecera
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

        ('BACKGROUND', (0, 1), (-1, -1), colors.white),  # Fondo de los datos
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),   # Color del texto de los datos
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),

        ('BOX', (0, 0), (-1, -1), 1, colors.black),      # Borde
        ('GRID', (0, 0), (-1, -1), 1, colors.black)      # Líneas de la cuadrícula
    ]))

    # Agregar la tabla a los elementos del PDF
    elements.append(table)

    # Generar el PDF
    pdf.build(elements)
    print(f"PDF generado: {pdf_file}")

 # Con formato requerido

general_info(api_key, start_date, end_date)





def general_rates_by_date(api_key, start_date, end_date):
    """
    Obtiene los datos desde el backend y genera un reporte PDF con acceso e ingresos por fecha.

    Args:
        api_key (str): La clave de API para autenticar la solicitud.
        start_date (str): Fecha de inicio en formato YYYY-MM-DDTHH:MM:SS.
        end_date (str): Fecha de fin en formato YYYY-MM-DDTHH:MM:SS.

    Returns:
        None
    """
    # Llamar a la función para obtener los datos del backend
    json_data = fetch_data_from_backend(api_key, start_date, end_date)
    if not json_data:
        print("No se pudo obtener los datos del backend. No se generará el PDF.")
        return

    # Procesar los datos obtenidos (acceder al primer elemento de la lista)
    first_data_item = json_data.get("data", [])[0]  # Obtener el primer elemento de la lista "data"
    results = first_data_item.get("data", {}).get("results", {})
    general_data = results.get("fechas", {})  # Acceder a las fechas

    # Prepare the PDF document
    pdf_file = "general_rates_by_date_report.pdf"
    pdf = SimpleDocTemplate(pdf_file, pagesize=letter)

    # Styles
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.alignment = 1
    subtitle_style = styles['Heading2']
    subtitle_style.alignment = 1

    # Table column widths
    col_width = (letter[0] - 20) / 8
    line_height = 18

    # Initialize totals
    total_pagos = total_amount = total_amount_usd = total_cash_ves = total_cash_usd = total_cash_cop = total_tc = 0

    # Initialize table data
    table_data = [
        ['Fecha', 'Pagos', 'Total general', 'TC', 'Total USD', 'Efvo. Bs', 'Efvo. USD', 'Efvo. COP']
    ]

    # Process the data and append it to table_data
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
            str(datetime.fromisoformat(date).strftime('%d-%m-%Y')),
            str(locale.format_string('%.0f', pagos_daily, True)),
            str(locale.format_string('%.2f', amount_daily, True)),
            str(locale.format_string('%.4f', exchange_rate_tc, True)),
            str(locale.format_string('%.2f', amount_daily_usd, True)),
            str(locale.format_string('%.2f', cash_ves, True)),
            str(locale.format_string('%.0f', cash_usd, True)),
            str(locale.format_string('%.0f', cash_cop, True)),
        ])

        # Update totals
        total_pagos += pagos_daily
        total_amount += amount_daily
        total_amount_usd += amount_daily_usd
        total_cash_usd += cash_usd
        total_cash_cop += cash_cop
        total_cash_ves += cash_ves
        total_tc += exchange_rate_tc  # Sum of TC

    # Add totals to the last row
    table_data.append([
        '',
        str(locale.format_string('%.0f', total_pagos, True)),
        str(locale.format_string('%.2f', total_amount, True)),
        str(locale.format_string('%.4f', total_tc, True)),  # Total TC
        str(locale.format_string('%.2f', total_amount_usd, True)),
        str(locale.format_string('%.2f', total_cash_ves, True)),
        str(locale.format_string('%.0f', total_cash_usd, True)),
        str(locale.format_string('%.0f', total_cash_cop, True))
    ])

    # Create the PDF elements
    elements = []
    
    # Add title and subtitle
    elements.append(Paragraph("Reporte de Ingresos y Accesos por Fecha", title_style))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph('Resumen de Accesos e Ingresos por Fecha', subtitle_style))
    elements.append(Spacer(1, 12))

    # Create the table
    table = Table(table_data, colWidths=[col_width] * 8, rowHeights=[line_height] * len(table_data))

    # Style the table
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.yellow),  # Header background
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),    # Header text color
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Header font
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),  # Data background
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),   # Data text color
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        
        ('BOX', (0, 0), (-1, -1), 1, colors.black),      # Border
        ('GRID', (0, 0), (-1, -1), 1, colors.black)      # Grid lines
    ]))

    # Add table to elements
    elements.append(table)

    # Build the PDF
    pdf.build(elements)
    print(f"PDF generado: {pdf_file}")


# Llamada a la función con formato correcto de fechas

general_rates_by_date(api_key, start_date, end_date)




def general_rates_by_vehicle(api_key, start_date, end_date):
    """
    Genera un informe detallado de las tarifas por vehículo, obteniendo los datos desde el backend.
    
    Args:
        api_key (str): La clave de API para autenticar la solicitud.
        start_date (str): Fecha de inicio en formato YYYY-MM-DDTHH:MM:SS.
        end_date (str): Fecha de fin en formato YYYY-MM-DDTHH:MM:SS.
    
    Returns:
        None
    """
    subtitle = 'Resumen de Tarifas General'

    print(f"Generando reporte: {subtitle}")

    # Obtener los datos del backend
    json_data = fetch_data_from_backend(api_key, start_date, end_date)
    if not json_data:
        print("No se pudo obtener los datos del backend. No se generará el PDF.")
        return

    # Procesar los datos obtenidos (acceder al primer elemento de la lista)
    first_data_item = json_data.get("data", [])[0]
    results = first_data_item.get("data", {}).get("results", {})
    general_data = results.get("tarifas", {})

    if not general_data:
        print("No se pudieron obtener los datos de tarifas. No se generará el reporte.")
        return

    # Procesar la información de los vehículos
    finals = []

    total_amount = 0
    total_ves_amount = 0
    total_pagos = 0
    total_ves_cash = 0
    total_usd_cash = 0
    total_cop_cash = 0

    for data in general_data.values():
        total_amount += data['cantidad']
        total_ves_amount += data["monto"]
        total_pagos += data["cantidad"]
        total_ves_cash += data["cash_collected"]["VES"]
        total_usd_cash += data["cash_collected"]["USD"]
        total_cop_cash += data["cash_collected"]["COP"]

    for data in general_data.values():
        amount = data["cantidad"]
        total = data["monto"]
        ves_cash = data["cash_collected"]["VES"]
        usd_cash = data["cash_collected"]["USD"]
        cop_cash = data["cash_collected"]["COP"]

        # Calcular porcentajes
        percentage_amount = (amount / total_amount) * 100
        percentage_ves_cash = (total / total_ves_amount) * 100

        finals.append(
            (
                str(data["nombre"]),
                str(locale.format_string('%.0f', amount, True)),
                f"{str(locale.format_string('%.2f', percentage_amount, True))}%",
                str(locale.format_string('%.2f', total, True)),
                f"{str(locale.format_string('%.2f', percentage_ves_cash, True))}%",
                str(locale.format_string('%.2f', ves_cash, True)),
                str(locale.format_string('%.0f', usd_cash, True)),
                str(locale.format_string('%.0f', cop_cash, True))
            )
        )

    # Ordenar los vehículos según el tipo
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

    # Agregar fila de totales
    totals_row = (
        "Total",
        str(locale.format_string('%.0f', total_pagos, True)),
        "",
        str(locale.format_string('%.2f', total_ves_amount, True)),
        "",
        str(locale.format_string('%.2f', total_ves_cash, True)),
        str(locale.format_string('%.0f', total_usd_cash, True)),
        str(locale.format_string('%.0f', total_cop_cash, True))
    )
    
    finals.append(totals_row)

    # Generación del reporte en formato PDF
    pdf_file = "general_rates_by_vehicle_report.pdf"
    pdf = SimpleDocTemplate(pdf_file, pagesize=letter)

    # Estilo
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.alignment = 1
    subtitle_style = styles['Heading2']
    subtitle_style.alignment = 1

    # Columnas y alturas
    col_width = (letter[0] - 20) / 8
    line_height = 18

    # Crear el contenido para el PDF
    elements = []
    
    # Agregar título y subtítulo
    elements.append(Paragraph("Reporte de Tarifas por Vehículo", title_style))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(subtitle, subtitle_style))
    elements.append(Spacer(1, 12))

    # Titulos de columnas
    column_titles = (
        'Tipo de Vehículo', 'Pagos', '% Pagos', 'Monto Total Bs', '% Monto Total Bs', 'Efectivo Bs', 'Efectivo USD', 'Efectivo COP'
    )
    finals.insert(0, column_titles)

    # Crear la tabla
    table = Table(finals, colWidths=[col_width] * 8, rowHeights=[line_height] * len(finals))

    # Estilo de la tabla
    table.setStyle(TableStyle([

        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), colors.yellow),  # Fondo del encabezado
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),    # Color del texto del encabezado
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Fuente del encabezado
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Datos
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),  # Fondo de los datos
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),   # Color del texto de los datos
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        
        # Bordes
        ('BOX', (0, 0), (-1, -1), 1, colors.black),      # Bordes
        ('GRID', (0, 0), (-1, -1), 1, colors.black)      # Líneas de la cuadrícula
    ]))

    # Agregar la tabla al documento
    elements.append(table)

    # Construir el PDF
    pdf.build(elements)
    print(f"PDF generado: {pdf_file}")



general_rates_by_vehicle(api_key = api_key, start_date = start_date, end_date = end_date)

def general_rates_by_payments(api_key, start_date, end_date):
    """
    Genera un informe detallado de los métodos de pago y sus respectivas tarifas.

    Este método obtiene los datos de pagos, los procesa para calcular totales y porcentajes 
    de cada método de pago, y organiza los datos en una tabla estructurada. La tabla incluye 
    diversos métricos financieros como transacciones totales, montos en Bolívares y porcentajes 
    de transacciones y montos recaudados.

    Atributos:
    - api_key (str): La clave API para autenticar la solicitud.
    - start_date (str): Fecha de inicio del reporte en formato YYYY-MM-DDTHH:MM:SS.
    - end_date (str): Fecha de fin del reporte en formato YYYY-MM-DDTHH:MM:SS.

    Retorna:
    - None
    """
    subtitle = 'Resumen de Métodos de Pago General'

    print(f"Generando reporte: {subtitle}")

    # Obtener los datos del backend
    json_data = fetch_data_from_backend(api_key, start_date, end_date)
    if not json_data:
        print("No se pudo obtener los datos del backend. No se generará el PDF.")
        return

    # Procesar los datos obtenidos (acceder al primer elemento de la lista)
    first_data_item = json_data.get("data", [])[0]
    results = first_data_item.get("data", {}).get("results", {})
    general_data = results.get("metodos_pago", {})

    if not general_data:
        print("No se pudieron obtener los datos de tarifas. No se generará el reporte.")
        return

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
    finals = []

    # Primero, acumular los totales por cada grupo (Dólares, Pesos, Bolívares)
    for group_key, group in general_data.items():
        if isinstance(group, dict):  # Verificamos que 'group' sea un diccionario
            for payment_key, data in group.items():
                if isinstance(data, dict):  # Verificamos que 'data' sea un diccionario
                    # Acumulando los totales
                    total_num_transactions += data.get('num_transactions', 0)
                    total_ves_amount += data.get("amount_pivoted", 0)

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

                        finals.append(
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

    # Agregar fila de totales
    totals_row = (
        "Total",
        str(locale.format_string('%.0f', total_num_transactions, True)),
        "",
        str(locale.format_string('%.2f', total_ves_amount, True)),
        "",
    )
    
    finals.append(totals_row)

    # Generación del reporte en formato PDF
    pdf_file = "general_rates_by_payments_report.pdf"
    pdf = SimpleDocTemplate(pdf_file, pagesize=letter)

    # Estilo
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.alignment = 1
    subtitle_style = styles['Heading2']
    subtitle_style.alignment = 1

    # Columnas y alturas
    col_width = (letter[0] - 20) / 5
    line_height = 18

    # Crear el contenido para el PDF
    elements = []
    
    # Agregar título y subtítulo
    elements.append(Paragraph("Reporte de Métodos de Pago", title_style))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(subtitle, subtitle_style))
    elements.append(Spacer(1, 12))

    # Títulos de columnas
    column_titles = (
        'Método de pago', 'Pagos', '% Pagos', 'Monto Total Bs', '% Monto Total Bs')
    finals.insert(0, column_titles)

    # Crear la tabla
    table = Table(finals, colWidths=[col_width] * 5, rowHeights=[line_height] * len(finals))

    # Estilo de la tabla
    table.setStyle(TableStyle([

        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), colors.yellow),  # Fondo del encabezado
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),    # Color del texto del encabezado
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Fuente del encabezado
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Datos
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),  # Fondo de los datos
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),   # Color del texto de los datos
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        
        # Bordes
        ('BOX', (0, 0), (-1, -1), 1, colors.black),      # Bordes
        ('GRID', (0, 0), (-1, -1), 1, colors.black)      # Líneas de la cuadrícula
    ]))

    # Agregar la tabla al documento
    elements.append(table)

    # Construir el PDF
    pdf.build(elements)
    print(f"PDF generado: {pdf_file}")


general_rates_by_payments(api_key = api_key, start_date = start_date, end_date = end_date)


# Importar las bibliotecas necesarias
from flask import Flask, render_template, request, send_file
import sqlite3
from collections import Counter
import threading
from collections import Counter
import matplotlib.pyplot as plt
import numpy as np

# Inicializar la aplicación Flask
app = Flask(__name__)

# Ruta de la base de datos SQLite configurada en IntelliJ IDEA para Chrome y Mozilla
DATABASE_PATH_CHROME = r"C:/Users/compu/AppData/Local/Google/Chrome/User Data/Default/Network/Cookies"
DATABASE_PATH_MOZILLA = (r"C:/Users/compu/AppData/Roaming/Mozilla/Firefox/Profiles/"
                         r"2dz6wwmu.default-release/cookies.sqlite")

# Consultas SQL para seleccionar todas las cookies
SQL_QUERY_CHROME = "SELECT * FROM cookies"
SQL_QUERY_MOZILLA = "SELECT * FROM moz_cookies"

# Función para establecer la conexión a la base de datos de cookies
def connect_to_cookies_db(db_path):
    return sqlite3.connect(db_path)

# Función para obtener los datos de las cookies
def fetch_cookies_data(conn, sql_query, browser):
    cursor = conn.cursor()
    cursor.execute(sql_query)
    if browser == 'chrome':
        cookies_data = cursor.fetchall()
    elif browser == 'mozilla':
        cookies_data = cursor.fetchall()
    else:
        cookies_data = []
    return cookies_data

# Función para obtener el top de páginas visitadas
def get_top_pages(cookies_data, n=5):
    page_counter = Counter(cookie[1] for cookie in cookies_data)
    top_pages = page_counter.most_common(n)
    return top_pages

# Función para obtener el número de páginas web sin repetición
def get_unique_pages(cookies_data):
    unique_pages = set(cookie[1] for cookie in cookies_data)
    return len(unique_pages)

# Función para obtener los nombres de usuario y contraseñas de las cookies
def get_user_password_records(cookies_data):
    user_password_records = []
    for cookie in cookies_data:
        # Almacenar los valores de las cookies como cadenas
        username = cookie[2]
        password = cookie[3]
        user_password_records.append((username, password))
    return user_password_records

# Función para obtener el número de cookies de sesión combinadas de Chrome y Mozilla
def get_num_session_cookies():
    # Conectar a la base de datos de Chrome y obtener cookies de sesión
    conn_chrome = connect_to_cookies_db(DATABASE_PATH_CHROME)
    cookies_data_chrome = fetch_cookies_data(conn_chrome, SQL_QUERY_CHROME, browser='chrome')
    num_session_cookies_chrome = sum(1 for cookie in cookies_data_chrome if cookie[8] == 0)  # Verificar la columna 'is_secure'
    conn_chrome.close()

    # Conectar a la base de datos de Mozilla y obtener cookies de sesión
    conn_mozilla = connect_to_cookies_db(DATABASE_PATH_MOZILLA)
    cookies_data_mozilla = fetch_cookies_data(conn_mozilla, SQL_QUERY_MOZILLA, browser='mozilla')
    num_session_cookies_mozilla = sum(1 for cookie in cookies_data_mozilla if cookie[9] == 1)  # Verificar la columna 'isSecure'
    conn_mozilla.close()

    # Devolver la suma de cookies de sesión de Chrome y Mozilla
    return num_session_cookies_chrome + num_session_cookies_mozilla

# Numero de Cookies Chrome-Mozilla get_num_cookies_chrome
def get_num_cookies_chrome(top_pages):
    conn_chrome = connect_to_cookies_db(DATABASE_PATH_CHROME)
    cookies_data_chrome = fetch_cookies_data(conn_chrome, SQL_QUERY_CHROME, browser='chrome')
    conn_chrome.close()
    visit_counts = Counter(cookie[4] for cookie in cookies_data_chrome)
    return [visit_counts[page] for page, _ in top_pages], len(cookies_data_chrome)  # Devolver solo el recuento total de cookies

# Numero de Cookies Chrome-Mozilla get_num_cookies_mozilla
def get_num_cookies_mozilla(top_pages):
    conn_mozilla = connect_to_cookies_db(DATABASE_PATH_MOZILLA)
    cookies_data_mozilla = fetch_cookies_data(conn_mozilla, SQL_QUERY_MOZILLA, browser='mozilla')
    conn_mozilla.close()
    visit_counts = Counter(cookie[3] for cookie in cookies_data_mozilla)
    return [visit_counts[page] for page, _ in top_pages], len(cookies_data_mozilla)  # Devolver solo el recuento total de cookies

# Función para generar una gráfica de barras de las páginas más visitadas
def generate_bar_chart(top_pages):
    pages, counts = zip(*top_pages)
    plt.figure(figsize=(15, 10))
    plt.bar(pages, counts, color='skyblue')
    plt.xlabel('Páginas')
    plt.ylabel('Visitadas')
    plt.title('Top Páginas Visitadas')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

# Función para obtener las visitas por host
def get_host_visits(cookies_data, browser):
    if browser == 'chrome':
        host_index = 1  # Índice del campo de dominio para Chrome
    elif browser == 'mozilla':
        host_index = 4  # Índice del campo de host para Mozilla
    else:
        raise ValueError("Unsupported browser type.")

    host_visits = Counter(cookie[host_index] for cookie in cookies_data)
    return host_visits

# Función para generar el gráfico de área
def generate_area_chart(host_visits):
    hosts, visits = zip(*host_visits.items())
    areas = np.array(visits) * 50  # Ajusta el factor de escala según sea necesario

    plt.figure(figsize=(15, 10))
    plt.fill_between(hosts, 0, areas, alpha=0.4)
    plt.plot(hosts, areas, marker='', color='red', linewidth=2)
    plt.xlabel('Hosts')
    plt.ylabel('Número de Cookies')
    plt.title('Número de Cookies por Host (Área)')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

# Ruta principal del dashboard
@app.route('/', methods=['GET', 'POST'])
def dashboard():
    if request.method == 'POST':
        top_pages_param = int(request.form['top_pages'])
    else:
        top_pages_param = 5


    # Establecer conexión a la base de datos de cookies de Chrome
    conn_chrome = connect_to_cookies_db(DATABASE_PATH_CHROME)
    # Obtener cookies de sesión de Chrome
    cookies_data_chrome = fetch_cookies_data(conn_chrome, SQL_QUERY_CHROME, browser='chrome')  # Pasar 'chrome' como el tipo de navegador
    # Cerrar la conexión
    conn_chrome.close()

    # Establecer conexión a la base de datos de cookies de Mozilla
    conn_mozilla = connect_to_cookies_db(DATABASE_PATH_MOZILLA)
    # Obtener cookies de sesión de Mozilla
    cookies_data_mozilla = fetch_cookies_data(conn_mozilla, SQL_QUERY_MOZILLA, browser='mozilla')  # Pasar 'mozilla' como el tipo de navegador
    # Cerrar la conexión
    conn_mozilla.close()

    #Obtener datos de la tabla
    cookies_combined = zip(cookies_data_chrome, cookies_data_mozilla)

    # Procesar los datos combinados de cookies
    num_unique_pages = get_unique_pages(cookies_data_chrome + cookies_data_mozilla)
    top_pages = get_top_pages(cookies_data_chrome + cookies_data_mozilla, top_pages_param)
    pages, counts = zip(*top_pages)  # Definir 'pages' aquí
    user_password_records_chrome = get_user_password_records(cookies_data_chrome)
    user_password_records_mozilla = get_user_password_records(cookies_data_mozilla)

    # Generar gráfica de barras de las páginas más visitadas
    generate_bar_chart(top_pages)

    # Guardar la gráfica generada
    #plt.savefig('top_pages_bar_chart.png')

    # Obtener datos de cookies de Chrome y Mozilla con conteos de visitas
    chrome_visit_counts, num_cookies_chrome = get_num_cookies_chrome(top_pages)
    mozilla_visit_counts, num_cookies_mozilla = get_num_cookies_mozilla(top_pages)

    # Obtener las visitas por host para Chrome y Mozilla
    host_visits_chrome = get_host_visits(cookies_data_chrome, 'chrome')
    host_visits_mozilla = get_host_visits(cookies_data_mozilla, 'mozilla')

    # Verificar si num_cookies_mozilla tiene al menos un elemento antes de acceder al recuento total de cookies
    if num_cookies_mozilla > 0:
        num_cookies_mozilla = num_cookies_mozilla
    else:
        num_cookies_mozilla = 0

    # Verificar si num_cookies_chrome tiene al menos un elemento antes de acceder al recuento total de cookies
    if num_cookies_chrome > 0:
        num_cookies_chrome = num_cookies_chrome
    else:
        num_cookies_chrome = 0

    # Generar los gráficos de área
    generate_area_chart(host_visits_chrome)
    #plt.savefig('chrome_cookies_area_chart.png')

    generate_area_chart(host_visits_mozilla)
    #plt.savefig('mozilla_cookies_area_chart.png')

    # Renderizar el template del dashboard con los datos combinados de Chrome y Mozilla
    return render_template('dashboards.html',
                           cookies_combined=cookies_combined,
                           num_unique_pages=num_unique_pages,
                           top_pages=top_pages,
                           pages=pages,  # Pasar 'pages' al contexto del template
                           counts=counts,  # Pasar 'counts' al contexto del template
                           user_password_records_chrome=user_password_records_chrome,
                           user_password_records_mozilla=user_password_records_mozilla,
                           num_session_cookies=get_num_session_cookies(),
                           host_visits_chrome=host_visits_chrome,
                           host_visits_mozilla=host_visits_mozilla,
                           list=list,
                           chrome_visit_counts=chrome_visit_counts,
                           mozilla_visit_counts=mozilla_visit_counts,
                           num_cookies_mozilla=num_cookies_mozilla,  # Acceder al primer elemento de la lista
                           num_cookies_chrome=num_cookies_chrome,  # Acceder al primer elemento de la lista
                           cookies_data_chrome=cookies_data_chrome,
                           cookies_data_mozilla=cookies_data_mozilla)

# Ruta para servir la imagen de la gráfica de barras de páginas más visitadas
#@app.route('/top_pages_bar_chart')
#def top_pages_bar_chart():
#    return send_file('top_pages_bar_chart.png', mimetype='image/png')

# Función para ejecutar la aplicación Flask
def run_flask():
    app.run(debug=True, use_reloader=False)

# Verificar si se está ejecutando como script principal
if __name__ == '__main__':
    # Iniciar el servidor Flask en un hilo separado
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

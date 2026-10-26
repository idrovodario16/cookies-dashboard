# Cookies Dashboard

Proyecto histórico de dashboard local para visualizar registros de cookies de Chrome y Firefox, separado del repositorio de perfil de Darío Idrovo.

## Qué hacía

La ruta principal de Flask leía las tablas SQLite `cookies` (Chrome) y `moz_cookies` (Firefox) desde rutas fijas de Windows. Preparaba datos para una plantilla Jinja con:

- Totales de cookies por navegador y una tabla paginada.
- Un ranking configurable que la interfaz llamaba «Top de páginas visitadas».
- Recuentos por dominio/host y gráficos con Chart.js.
- Indicadores etiquetados como páginas únicas, cookies de sesión y usuarios encontrados.
- Una sección «Usuario - Contraseñas» basada en posiciones de columnas de las filas.

El formulario POST cambiaba la cantidad de elementos del ranking. No había cuentas de usuario, permisos ni un backend remoto de recolección: la aplicación consultaba archivos locales y mostraba el resultado en una interfaz web.

## Tecnologías

| Capa | Tecnología |
| --- | --- |
| Servidor local | Python y Flask |
| Plantillas | Jinja, HTML y Bootstrap 4 |
| Gráficos web | Chart.js |
| Acceso a archivos de datos | SQLite mediante sqlite3 |
| Gráficos adicionales en Python | Matplotlib y NumPy |

## Limitaciones del código conservado

Esta separación conserva los archivos originales sin corregir su comportamiento.

1. **Cookies no equivalen a visitas.** El ranking cuenta filas de cookies; no consulta el historial de navegación. Sus etiquetas no demuestran frecuencia real de visitas.
2. **No recupera contraseñas guardadas.** `get_user_password_records` toma las columnas 2 y 3 y las llama usuario y contraseña sin comprobar su significado; no consulta el almacén de contraseñas ni implementa descifrado.
3. **Supone posiciones fijas de columnas.** Usa `SELECT *` e índices distintos entre funciones. Los indicadores de dominio, sesión, seguridad y expiración requieren revisar el esquema de cada navegador.
4. **La tabla puede omitir registros.** Empareja las filas de ambos navegadores con `zip`, que se detiene al terminar la lista más corta.
5. **Depende de rutas de un equipo Windows concreto.** También puede fallar si los archivos no existen, están bloqueados o los esquemas cambian. No maneja adecuadamente esos errores ni los resultados vacíos.
6. **El CSS no tiene una ruta de servicio configurada.** Está dentro de `templates/`, pero la página lo solicita como `styles.css`.
7. **Modo de desarrollo.** Activa `debug=True` y no tiene autenticación. No está preparado para producción.

Matplotlib genera figuras, pero las instrucciones para guardarlas y servirlas están comentadas; los gráficos visibles de la plantilla usan Chart.js.

## Archivos

- `app.py`: consultas, cálculos y ruta principal de Flask.
- `templates/dashboards.html`: dashboard, gráficos y paginación.
- `templates/styles.css`: estilos originales.
- `.idea/` y `cookies_dashboard.iml`: configuración histórica del editor, conservada como parte del proyecto original.

## Estado de verificación y uso

La separación se verificó comparando los SHA de los archivos originales y sus copias. No se ejecutó contra perfiles reales de navegador ni se confirmó funcionamiento integral. No se incluyen bases de cookies ni datos de navegación.

Para una futura demostración, conviene usar bases ficticias y corregir las limitaciones anteriores. Los valores de cookies pueden ser sensibles: no deben publicarse, usarse en capturas compartidas ni subirse al repositorio.

## Procedencia

Archivos extraídos de `idrovodario16/idrovodario16`, rama `master`, commit `ec79984a0f20fad922cc4449909281226184ce66`. El historial original sigue disponible en ese repositorio; esta copia inicia una historia independiente y no reescribe el historial anterior.

# Validación de la versión 2.0

Fecha: 2026-10-26. Solo se utilizaron datos ficticios.

## Comprobaciones ejecutadas

| Comprobación | Resultado |
| --- | --- |
| `python -m pytest` | 30 pruebas aprobadas en Python 3.12 |
| `node --test tests/test_reports.cjs` | 4 pruebas aprobadas |
| `node --check static/app.js` | Sintaxis válida |
| Demo en navegador de escritorio | 36 registros; 6 dominios; métricas y gráficos visibles |
| Búsqueda por `tienda.example` | 12 registros |
| Filtro Secure = No sobre esa selección | 3 registros |
| Búsqueda sin coincidencias | Estado vacío y exportación desactivada |
| Paginación | Segunda página: registros 13–24 de 36 |
| Guía y diálogo | Navegación, apertura y cierre comprobados |
| Descarga JSON desde la interfaz | 36 registros; contenido JSON y exclusión de valores comprobados |
| API de importación con Flask test client | Una y dos bases, errores, CSRF, origen, host y limpieza comprobados |

## Límites de estas comprobaciones

La vista previa de escritorio utilizó el HTML renderizado por Flask, los mismos CSS/JavaScript y una respuesta JSON de demo congelada. El proceso de vista previa no tenía disponible el intérprete de Python de la aplicación; por eso **no se comprobó la carga de archivos de extremo a extremo desde ese navegador contra un servidor Flask vivo**. Esa API se verificó por separado mediante Flask test client y SQLite sintético.

No se analizaron perfiles reales, no se validó la compatibilidad con todas las versiones de Chrome/Firefox y no se emuló un dispositivo móvil. La adaptación a pantallas estrechas está definida en CSS; falta comprobarla en dispositivos reales.

El workflow de GitHub Actions incluye Python 3.12 y 3.13. La ejecución local realizada no sustituye el resultado de esos jobs en GitHub.

## Revisión previa a hacer público el código

Se revisaron los dos commits históricos existentes y los archivos de esta versión buscando credenciales y bases de cookies. El historial conserva configuración antigua del IDE y rutas de ejemplo del equipo original, pero no se encontraron tokens, claves privadas ni bases de navegación. Los archivos de IDE no forman parte de la versión actual.

Una búsqueda de patrones no garantiza que un repositorio esté libre de cualquier dato sensible. No se publican archivos importados, reportes reales ni estado local del entorno de desarrollo.

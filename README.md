# Cookies Privacy Analyzer

Herramienta local para explorar metadatos de cookies de Chrome/Chromium y Firefox mediante copias SQLite autorizadas.

**Stack:** Python/Flask, SQLite, HTML/Jinja, CSS y JavaScript.

**Estado:** herramienta educativa local y demo estática con datos ficticios. No descifra valores ni realiza una auditoría automática de seguridad.

[Demo web](https://idrovodario16.github.io/cookies-dashboard/)

## Qué puedes hacer

- Explorar una demo de 36 cookies sintéticas sin seleccionar ningún archivo.
- Analizar una o dos copias SQLite consolidadas: tablas `cookies` o `moz_cookies`.
- Consultar nombre, dominio, ruta, expiración UTC, `Secure`, `HttpOnly` y `SameSite`.
- Filtrar por navegador, dominio/nombre, estado y atributos.
- Comparar recuentos por dominio sin confundir cookies con visitas.
- Exportar la selección a CSV o JSON; el JSON incluye filtros, advertencias y procedencia.
- Consultar la huella SHA-256 de cada copia procesada.
- Usar una interfaz adaptable con navegación por teclado, estados vacíos y mensajes de error.

## Inicio rápido

Necesitas **Python 3.12 o superior**. No necesitas Node.js para ejecutar la aplicación.

```bash
git clone https://github.com/idrovodario16/cookies-dashboard.git
cd cookies-dashboard
python -m venv .venv
```

Activa el entorno:

```bash
# Linux / macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Instala y arranca:

```bash
python -m pip install -r requirements.txt
python app.py
```

Abre **http://127.0.0.1:5000**. Aparece primero la demo. El servidor se enlaza a loopback y arranca sin modo depuración; no necesita claves API, bases externas ni cuenta de usuario. Los estilos y scripts se sirven localmente, sin CDN, fuentes externas ni telemetría de la aplicación.

Para detenerlo, pulsa `Ctrl+C`. Si el puerto está ocupado, detén el otro proceso o cambia conscientemente el puerto local en `app.py`; no expongas el servidor a internet.

## Probar importación con archivos ficticios

```bash
python scripts/create_demo_snapshots.py
```

Se crean dos archivos ignorados por Git en `demo-data/`:

- `chromium-demo.sqlite`: 8 registros ficticios.
- `firefox-demo.sqlite`: 5 registros ficticios.

Pulsa **Analizar copia SQLite**, selecciona ambos y comprueba los **13 registros**. Las tablas no se emparejan con `zip`, por lo que una base más pequeña no provoca la pérdida de filas de la otra. El generador no reemplaza archivos existentes.

## Uso de copias reales y límites

1. Trabaja únicamente con datos propios o autorizados y prepara una copia de la base.
2. Usa una **instantánea SQLite consolidada y cerrada**. Copiar solo el archivo principal de una base activa puede omitir cambios pendientes del WAL. Una copia obtenida con el mecanismo de backup de SQLite es preferible a copiar un archivo activo sin coordinar sus archivos auxiliares.
3. Selecciona hasta **dos archivos, de 8 MiB cada uno**. El límite de la solicitud completa es 17 MiB, contando su envoltura HTTP.
4. Se procesan hasta **5.000 filas por archivo**, con un límite temporal de consulta de aproximadamente dos segundos. Si hay más, el resultado indica explícitamente que es una muestra parcial. No se garantiza el orden ni que sea una muestra representativa.
5. Revisa las advertencias. «Desconocido» significa que el esquema no aporta el dato o no es interpretable; no se sustituye automáticamente por «No».

Solo se aceptan tablas ordinarias con columnas de dominio y nombre reconocibles. Se rechazan vistas, tablas virtuales, columnas generadas/ocultas y bases con ambos esquemas de navegador. Se detectan archivos WAL/journal adyacentes cuando el analizador recibe rutas locales, pero **la importación web no puede detectar un WAL que no hayas seleccionado**. La completitud de la instantánea depende de cómo se preparó.

La aplicación no incluye una garantía de compatibilidad con todas las versiones de los navegadores. Las bases cifradas, otros formatos o esquemas nuevos pueden ser rechazados o mostrar metadatos parciales.

## Cómo interpretar los resultados

| Dato | Significado y límite |
| --- | --- |
| Cookies analizadas | Filas de la selección actual; no representa visitas ni personas. |
| Dominios únicos | Dominios almacenados, agrupando mayúsculas y un punto inicial. No se agrupan subdominios por dominio registrable. |
| Secure | Atributo declarado que restringe el transporte según las reglas del navegador; su ausencia necesita contexto. |
| HttpOnly | Restricción de acceso desde scripts. Algunas cookies legítimas deben ser accesibles desde JavaScript. |
| SameSite | Política almacenada. «No especificado» no equivale a `None`; el navegador puede aplicar valores por defecto. |
| Sesión | En Chromium se usan `has_expires`, `is_persistent` o expiración cero según disponibilidad. En Firefox se necesita `isSession`; si falta, no se afirma que sea una cookie de sesión. |
| Vencida / Vigente | Comparación de una fecha interpretable con el instante de análisis. «Vigente» solo describe esa fecha, no la validez de una sesión ni de un sitio. |
| SHA-256 | Identifica los bytes de la copia recibida; no acredita procedencia, integridad previa ni cadena de custodia. |

El porcentaje Secure usa únicamente registros con ese atributo conocido como denominador. Los gráficos, indicadores y exportaciones cambian con los filtros. La agrupación por dominio **no clasifica automáticamente rastreadores ni cookies de terceros**; para ello haría falta contexto adicional del sitio visitado.

No se calcula una puntuación global de seguridad: un indicador aislado no demuestra una vulnerabilidad.

## Privacidad y manejo de archivos

- No se buscan carpetas del navegador ni se consulta el historial de navegación o el almacén de contraseñas.
- El SQL usa una lista cerrada de columnas de metadatos: **no selecciona `value` ni `encrypted_value`**.
- Al importar, **el archivo SQLite completo** se transmite al proceso Flask y se escribe en un directorio temporal aleatorio. Por ello, el archivo puede contener valores sensibles aunque no se consulten ni devuelvan. En el uso recomendado Flask corre en tu propio equipo.
- Las conexiones usan `mode=ro`, `immutable=1`, `query_only=ON` y `trusted_schema=OFF`. Los archivos deben ser instantáneas estables; no se modifican durante el análisis.
- Los temporales se eliminan al finalizar la solicitud, también ante errores controlados. Esto no es borrado seguro: una terminación abrupta del proceso puede dejar temporales para la limpieza del sistema operativo.
- Los resultados se conservan en memoria de la pestaña; no se guardan en localStorage, base de datos de la aplicación ni cuentas. Al recargar, se vuelve al modo demo.
- Los reportes excluyen valores, pero **dominios, nombres y rutas pueden revelar información personal**. Revísalos antes de compartirlos. Los reportes descargados permanecen en tu equipo hasta que los elimines.
- No se registran archivos, resultados ni contenido de cookies en los logs de la aplicación. Flask puede mostrar logs HTTP básicos.

El servidor rechaza nombres de host ajenos a loopback, valida el token CSRF y el origen de cargas cuando está presente, limita tamaño y tiempo de consulta, y sirve una política CSP sin scripts externos. El CSV neutraliza prefijos de fórmulas comunes. Estas defensas no convierten al proceso en un sandbox de archivos maliciosos; usa versiones actualizadas de Python/SQLite y archivos de procedencia conocida.

**Repositorio público no significa servicio público.** Este proyecto se distribuye para ejecución local. No contiene autenticación multiusuario, aislamiento entre clientes ni infraestructura para recibir archivos sensibles desde internet. No despliegues este servidor como un analizador público sin rediseñar esas partes.

## Arquitectura y tecnologías

| Capa | Tecnología |
| --- | --- |
| Backend y API local | Python y Flask |
| Lectura y normalización | `sqlite3` de la biblioteca estándar |
| Interfaz | HTML/Jinja, CSS y JavaScript sin dependencias de frontend |
| Gráficos | Barras construidas con HTML/CSS y recuentos de metadatos |
| Pruebas | pytest; SQLite sintético en directorios temporales |
| Integración continua | GitHub Actions, Python 3.12 y 3.13 |

```text
app.py                         Aplicación Flask, límites y rutas
analyzer.py                    Detección de esquema, normalización y demo
templates/index.html           Interfaz y guía de interpretación
static/                        Estilos, scripts e icono
scripts/create_demo_snapshots.py Generador de SQLite ficticio
tests/                         Pruebas de análisis, privacidad y API
docs/                          Captura ficticia y notas de cambios
.github/workflows/tests.yml    Comprobaciones automáticas
```

| Ruta | Comportamiento |
| --- | --- |
| `GET /` | Interfaz y token CSRF de sesión |
| `GET /api/demo` | Metadatos sintéticos |
| `POST /api/analyze` | Multipart `files`, uno o dos archivos, cabecera `X-CSRF-Token`; devuelve metadatos sin valores |
| `GET /health` | Estado básico del proceso |

La sesión firmada almacena únicamente el token CSRF, nunca la base ni el resultado. Su clave se genera en memoria al arrancar; reiniciar requiere recargar la página.

## Pruebas y validación

```bash
python -m pip install -r requirements-dev.txt
python -m pytest

# Opcional, si tienes Node.js instalado
node --check static/app.js
node --test tests/test_reports.cjs
```

Las pruebas cubren diferencias de esquema, fechas, atributos desconocidos, límites de muestra, ausencia de valores en respuestas, archivos inválidos, tablas no admitidas, preservación de bytes de entrada, CSRF, host/origen, carga de dos archivos y limpieza de temporales. No acceden a perfiles reales.

Los resultados y límites de las pruebas están en [docs/VALIDATION.md](docs/VALIDATION.md); la evolución respecto al proyecto original está en [CHANGELOG.md](CHANGELOG.md). Las comprobaciones automáticas no demuestran compatibilidad con todos los navegadores ni sustituyen una auditoría de seguridad.

## Evolución del proyecto

La versión inicial era un dashboard en Flask, Bootstrap, Chart.js, Matplotlib y NumPy con rutas Windows fijas. Mezclaba columnas entre navegadores, confundía cookies con visitas y etiquetaba datos como usuario/contraseña sin validarlos.

La versión 2 conserva la finalidad educativa, sustituye esas interpretaciones por metadatos explícitos, elimina el acceso automático a perfiles y reduce las dependencias a Flask. Los archivos originales continúan en el historial de Git; los archivos de IDE se han retirado de la versión actual.

## Referencias técnicas

- [Flask: configuración y límites](https://flask.palletsprojects.com/en/stable/config/)
- [Flask: consideraciones de seguridad](https://flask.palletsprojects.com/en/stable/web-security/)
- [SQLite: lectura de bases de procedencia no confiable](https://www.sqlite.org/security.html)
- [SQLite: PRAGMA y opciones de conexión](https://www.sqlite.org/pragma.html)
- [SQLite: Online Backup API](https://www.sqlite.org/backup.html)

## Autor y alcance

[Darío Idrovo](https://github.com/idrovodario16). Proyecto de portafolio y aprendizaje en desarrollo web, sistemas y privacidad. Las dependencias conservan sus propias licencias.


## Demo para GitHub Pages

Versión pública de la interfaz con 36 metadatos ficticios, filtros, indicadores y exportación CSV/JSON. No recibe archivos SQLite ni consulta perfiles. El análisis de copias reales sigue disponible exclusivamente en la aplicación local con Flask.

**Demo pública:** [Abrir Cookies Privacy Analyzer](https://idrovodario16.github.io/cookies-dashboard/). Publicada en GitHub Pages mediante GitHub Actions.


La carpeta `demo/` es estática y no necesita Python. Para previsualizarla sirve esa carpeta con un servidor local.

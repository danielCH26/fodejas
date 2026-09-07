# Spec Delta — `data-migration` (CHG-099)

> Delta para CHG-099. Bloques `## ADDED` según plantilla OpenSpec.

## ADDED

### Requirement: Comando `migrate_legacy_data`

El proyecto SHALL exponer un comando de gestión Django
`python manage.py migrate_legacy_data` que ingiere datos legacy
desde un directorio configurable. El comando SHALL ser **idempotente**:
corridas repetidas con el mismo input NO SHALL crear duplicados
(búsqueda por clave natural: `radicado` para `Solicitud`, `numero`
para `ActoAdministrativo`, `codigo` para `Convocatory`,
`documento` (anonimizado) para `CustomUser`, `convocatoria.codigo`
para `ListadoDefinitivo`).

El comando SHALL aceptar las siguientes opciones:

- `--source=<dir>` (requerido): directorio donde están los CSV.
- `--dry-run`: no escribe a la DB, sólo imprime el reporte de lo
  que se crearía.
- `--skip-validation`: omite la validación (uso de emergencia).
- `--anonymize-salt=<env>`: variable de entorno con el salt de
  anonimización. Default: `LEGACY_DATA_SALT`. Si no está seteada en
  producción, el comando DEBE abortar.

El comando DEBE retornar código de salida 0 si la migración fue
exitosa (incluso si fue dry-run), y código 1 si la validación
falló, los archivos no existen, o se violó una FK.

#### Scenario: Migración exitosa desde directorio válido

- **WHEN** el operador ejecuta `python manage.py
      migrate_legacy_data --source=/secure/path/`,
- **THEN** los 5 CSVs son leídos, validados, anonimizados y los
  registros creados en sus modelos correspondientes,
- **AND** el comando retorna exit code 0,
- **AND** el reporte se imprime con conteos por modelo.

#### Scenario: Corrida idempotente

- **WHEN** el operador ejecuta el comando dos veces con el mismo
  `--source`,
- **THEN** la segunda corrida NO crea duplicados,
- **AND** el conteo total de cada modelo es idéntico al de la
  primera corrida.

#### Scenario: Validación falla

- **WHEN** el operador ejecuta el comando con un CSV que le falta
      una columna esperada,
- **THEN** el comando aborta con exit code 1,
- **AND** NO se escribe ningún registro a la DB,
- **AND** el reporte imprime la columna faltante y la fila
  problemática.

### Requirement: Schemas de los archivos de entrada

Los 5 archivos CSV esperados DEBEN respetar los headers
documentados en `docs/migrations/data-schemas.md`:

| Archivo | Modelo destino | Clave natural |
|---------|----------------|---------------|
| `convocatorias.csv` | `Convocatory` | `codigo` |
| `solicitudes.csv` | `Solicitud` | `radicado` |
| `usuarios_legacy.csv` | `CustomUser` | `documento` (anonimizado) |
| `actos_legacy.csv` | `ActoAdministrativo` | `numero` |
| `listados_legacy.csv` | `ListadoDefinitivo` | `convocatoria.codigo` |

Cada archivo DEBE tener exactamente las columnas documentadas. La
validación DEBE rechazar archivos con columnas faltantes o extras.

### Requirement: Anonimización obligatoria

Cualquier campo que pueda contener PII SHALL pasarse por
`apps.core.migrations.anonymize.anonymize_hash(value, salt)` antes
de persistirse. La anonimización es **determinista** y
**reversible-bajo-llave**: con el mismo `salt`, el mismo input
produce el mismo output. Esto permite re-ejecuciones idempotentes
de la migración sin duplicar registros anonimizados.

Los campos que DEBEN anonimizarse son: `nombre`, `email`,
`documento`, `teléfono`, `dirección`, `datos_personales.*`,
`datos_académicos.*`, `datos_socioeconómicos.*`, `observaciones`,
`descripción`, `argumentos` (de Apelación).

Los campos que NO DEBEN anonimizarse (necesarios para auditoría
institucional): `radicado`, `numero`, `codigo`, `uuid`, timestamps,
FKs.

### Requirement: Validación previa

Antes de cualquier INSERT, el comando DEBE validar:

1. Todos los archivos existen en `--source` y son legibles.
2. Cada fila tiene su clave natural (no vacía, único dentro del
   archivo).
3. Las FKs entre archivos se satisfacen: por ejemplo, cada
   `Solicitud.convocatoria_codigo` debe existir en
   `convocatorias.csv`.
4. Ningún campo PII crudo está presente: el validador
   `validate_no_pii` corre regex contra emails / documentos /
   teléfonos obvios.

Si cualquier validación falla, el comando DEBE abortar SIN
escribir ningún registro, imprimir el reporte de validación y
retornar exit code 1.

### Requirement: Detección de PII crudo

El comando SHALL correr `validate_no_pii(csv_dataframe,
pii_columns)` que aplica regex contra:
- emails (`@example.com`, `@gmail.com`, etc.),
- documentos de identidad (secuencias de 7-10 dígitos consecutivos),
- teléfonos (secuencias de 10 dígitos con formato colombiano
  `3\d{9}`).

Si se detecta PII crudo en una columna que DEBÍA estar
anonimizada, el comando aborta y reporta la fila + columna
específica.

#### Scenario: PII detectado en columna anonimizada

- **WHEN** una fila en `usuarios_legacy.csv` tiene
      `email=alguien@example.com` (PII crudo),
- **THEN** el validador `validate_no_pii` retorna False,
- **AND** el comando aborta con exit code 1, reportando la fila
  específica.

# project.md — Plataforma FODEJAS

> Documento raíz del proyecto bajo la metodología **OpenSpec**.
> Define el propósito, el dominio, los actores, las capacidades, los flujos
> de negocio y las reglas de negocio que la plataforma debe soportar. Los
> detalles de comportamiento, los atributos de las entidades y los cambios
> incrementales se gestionan en `specs/<capability>/spec.md` y
> `changes/<change-id>/`.

---

## Tabla de Contenido

1. [Propósito del Proyecto](#1-propósito-del-proyecto)
2. [Contexto Institucional y Normativo](#2-contexto-institucional-y-normativo)
3. [Glosario Institucional y Abreviaturas](#3-glosario-institucional-y-abreviaturas)
4. [Stack Tecnológico](#4-stack-tecnológico)
5. [Convenciones del Proyecto](#5-convenciones-del-proyecto)
6. [Contexto del Dominio — El Fondo FODEJAS](#6-contexto-del-dominio--el-fondo-fodejas)
7. [Actores / Roles del Sistema](#7-actores--roles-del-sistema)
8. [Capacidades del Sistema (Catálogo)](#8-capacidades-del-sistema-catálogo)
9. [Modelo de Dominio](#9-modelo-de-dominio)
10. [Flujos de Negocio End-to-End](#10-flujos-de-negocio-end-to-end)
11. [Reglas de Negocio Críticas](#11-reglas-de-negocio-críticas)
12. [Convocatoria de Referencia — Cerrada "Reconocimiento a la Excelencia" 2026-1](#12-convocatoria-de-referencia--cerrada-reconocimiento-a-la-excelencia-2026-1)
13. [Seguridad, Auditoría y Cumplimiento](#13-seguridad-auditoría-y-cumplimiento)
14. [Reportes y Transparencia](#14-reportes-y-transparencia)
15. [Supuestos, Restricciones y Alcance](#15-supuestos-restricciones-y-alcance)
16. [Referencias Normativas](#16-referencias-normativas)

---

## 1. Propósito del Proyecto

### 1.1 Visión

Construir una **plataforma web Full Stack en Django + PostgreSQL** que
**digitalice y dé trazabilidad end-to-end al proceso de publicación,
ejecución, seguimiento, control y cierre de las convocatorias del FONDO
PARA EL DESARROLLO EDUCATIVO DE LOS JÓVENES DEL ARCHIPIÉLAGO (FODEJAS)**,
administrado por la Secretaría de Educación Departamental del
Archipiélago de San Andrés, Providencia y Santa Catalina.

### 1.2 Misión

Sustituir el flujo actual (presencial, basado en formularios físicos FUI,
carpetas, sellos manuales y hojas de cálculo) por un sistema único que
permita a cada uno de los actores del proceso gestionar su rol, dejando
constancia inmutable de cada acción.

### 1.3 Objetivos

- Centralizar la **publicación de convocatorias** (cerradas, públicas,
  por mérito, por vulnerabilidad, por áreas prioritarias, etc.).
- Permitir a los **aspirantes** registrarse, radicar el FUI digital con
  anexos y consultar el estado de su solicitud.
- Permitir al **Coordinador Técnico del FODEJAS**, al **Comité Técnico**
  y a la **Junta de Administración** gestionar el ciclo: validación de
  requisitos, calificación, reclamaciones, apelaciones, aprobación de
  listados, legalización de créditos y autorización de desembolsos.
- Permitir a la **Tesorería General** ejecutar los giros con un flujo de
  pagos trazable, con plazos y responsables claros.
- Garantizar **transparencia, rendición de cuentas, auditoría y
  protección de datos personales**.

### 1.4 Fuera del Alcance

- **Pagos desde la plataforma**: la plataforma **ordena** los pagos a la
  Tesorería, pero la transacción bancaria se realiza en los sistemas
  del Banco. **No existe integración con sistemas bancarios**.
- **Integración con sistemas externos**: la plataforma **no se integra**
  con SNIES, SISBÉN ni OCCRE. La verificación contra estos sistemas se
  realiza de manera manual o mediante consulta externa que el
  responsable de verificación gestiona por su cuenta; el resultado se
  registra en la plataforma como evidencia.
- **Reemplazo del documento soporte formal**: la firma del pagaré y la
  carta de instrucciones se digitaliza, pero el documento formal sigue
  los formatos del FODEJAS; la plataforma lo soporta como registro
  previo a la firma.
- **Firma física en ventanilla**: la inscripción puede hacerse
  digital, pero el proceso conserva la opción de radicación presencial
  con escaneo de la documentación.

---

## 2. Contexto Institucional y Normativo

### 2.1 Marco Normativo Aplicable

La plataforma debe reflejar, en sus reglas de negocio y validaciones, el
siguiente marco jurídico.

#### 2.1.1 Normativa Nacional

- **Constitución Política de Colombia**, Arts. 2, 44, 67, 69, 298, 300 y
  305.
- **Ley 30 de 1992** — Servicio público de Educación Superior.
- **Ley 115 de 1994** — Ley General de Educación.
- **Ley 1012 de 2006** — Reformas a los Arts. 111 y 114 de la Ley 30 de
  1992 sobre créditos departamentales y municipales para educación
  superior.
- **Ley 715 de 2001** — Recursos y competencias de las entidades
  territoriales certificadas en educación.
- **Ley 1437 de 2011 (CPACA)** — Código de Procedimiento Administrativo
  y de lo Contencioso Administrativo: notificaciones, recursos,
  correcciones de actos administrativos, términos.
- **Ley 1474 de 2011** — Estatuto Anticorrupción.
- **Ley 1952 de 2019** — Código General Disciplinario (inhabilidades e
  incompatibilidades aplicables a miembros de la Junta).
- **Ley 2200 de 2022** — Código Electoral, Art. 119 numeral 12.
- **Ley 1885 de 2018**, **Decreto 859 de 2015** — delegación de
  funciones.
- **Ley 909 de 2004** y **Decreto 1083 de 2015** — Función pública y
  empleo.
- **Decreto 2762 de 1991** — Situación de residencia en el Archipiélago.
- **Decreto 1075 de 2015** (Arts. 2.5.3.2.2.5 y ss.), modificado por el
  **Decreto 1330 de 2019** — Modalidades de estudio.
- **Ley 1581 de 2012** y **Decreto 1377 de 2013** — Protección de datos
  personales.
- **Decreto 4631 de 2011** y **Resolución 111763 de 2023** — Reparación
  colectiva del Pueblo Raizal.

#### 2.1.2 Normativa Departamental

- **Ordenanza No. 005 de 2024 (31 de mayo)** — Plan de Desarrollo
  Departamental 2024-2027 "El Archipiélago Avanza", apuesta
  "Dignidad", Programa No. 4 "Avanzando hacia el mejoramiento de
  oportunidades de acceso a la educación superior", meta "Apoyo
  Financiero con nuevos créditos, becas educativas de pregrado y post
  grado".
- **Ordenanza No. 007 de 2025 (29 de abril)** — Crea el FODEJAS,
  define su naturaleza, estructura, recursos, modalidades de apoyo,
  población prioritaria, sanciones y garantías.
- **Decreto Departamental No. 0372 de 2025 (12 de agosto)** —
  Reglamenta la Ordenanza 007, adopta el Manual Operativo, define
  condiciones de acceso, obligaciones del beneficiario, causales de
  terminación, condonación y sanciones.
- **Decreto Departamental No. 0072 de 2026 (09 de febrero)** — Asigna
  al Tesorero General las funciones de manejo de cuentas,
  procedimiento y plazo de pago del FODEJAS.
- **Decreto Departamental No. 0122 de 2026 (06 de marzo)** — Delega en
  el Secretario de Educación la ordenación del gasto del FODEJAS y la
  presidencia de la Junta de Administración.
- **Manual Operativo del FODEJAS** — Adoptado como parte integral del
  Decreto 0372/2025.

### 2.2 Problemática

El Archipiélago presenta:

- **Baja cobertura de educación superior**: parte significativa de los
  jóvenes no continúa su proceso formativo por falta de recursos para
  matrícula, transporte, materiales y sostenimiento.
- **Oferta académica limitada en el territorio insular**: obliga a
  estudiar fuera del Archipiélago, incrementando los costos de
  sostenimiento.
- **Vulnerabilidad socioeconómica** concentrada en los estratos 1, 2 y
  3 y en los grupos SISBÉN A, B y C.
- **Pérdida de capital humano**: los profesionales formados fuera del
  Archipiélago no retornan, debilitando la atención en salud,
  educación, turismo, ambiente, TIC, trilingüismo, integración
  fronteriza y derechos del Pueblo Raizal.

### 2.3 Finalidad del FODEJAS (Art. 3 Ordenanza 007/2025)

> *"Promover el acceso, la permanencia y la graduación de la educación
> terciaria y universitaria dentro del País como en el exterior,
> priorizando a los estudiantes pertenecientes al grupo étnico Raizal en
> condiciones de vulnerabilidad económica, méritos académicos,
> deportistas destacados y proyección social, a través de mecanismos
> de apoyo financiero que se otorgarán conforme a los principios de
> equidad, mérito, sostenibilidad y pertinencia territorial."*

### 2.4 Naturaleza Jurídica del FODEJAS

- **Fondo especial** sin personería jurídica.
- **Naturaleza**: contable y presupuestal.
- **Destinación**: administración separada de recursos públicos para
  financiar educación superior (pregrado y postgrado) y apoyos de
  manutención.
- **Adscripción**: a cargo de la Secretaría de Educación Departamental.
- **Funcionamiento**: cuenta especial dentro del Presupuesto General
  del Departamento.
- **Principios rectores**: universalidad, especialización, legalidad
  presupuestal, equidad, mérito, sostenibilidad y pertinencia
  territorial.

### 2.5 Cobertura Geográfica y Poblacional

- **Territorio**: Archipiélago de San Andrés, Providencia y Santa
  Catalina (incluye Providencia Isla con regla especial de excepción).
- **Población objetivo principal**: residentes del Archipiélago y
  miembros del Pueblo étnico Raizal.
- **Población prioritaria** (Art. 8 Manual Operativo y Art. 11
  Ordenanza 007):
  1. Estudiantes de instituciones públicas.
  2. Víctimas del conflicto armado (reparación colectiva del Pueblo
     Raizal).
  3. Personas en situación de discapacidad.
  4. Estudiantes pertenecientes al Grupo Étnico Raizal.
  5. Mejores puntajes de instituciones oficiales y privadas (estratos
     1, 2, 3).
  6. Estudiantes con alto rendimiento académico.
  7. Deportistas destacados.

### 2.6 Cobertura por Nivel de Formación

El FODEJAS financia **todos los niveles** de educación terciaria y
superior (pregrado y postgrado):

- **Pregrado**: técnico profesional, tecnológico, profesional
  universitario.
- **Postgrado**: especialización, maestría, doctorado.

**Distribución de recursos** (Art. 19 Ordenanza 007/2025):

- **80%** → pregrado.
- **20%** → maestrías y doctorados en áreas de alta demanda para la
  región insular (nacionales y en el exterior).

### 2.7 Áreas Prioritarias

El Fondo prioriza programas académicos estratégicos para el desarrollo
insular y regional (Art. 16 Ordenanza 007/2025):

- Ciencias de la salud.
- Ciencias de la educación y licenciaturas de áreas básicas
  (matemáticas, física, química).
- Tecnologías de la información y las comunicaciones (TIC).
- Turismo sostenible.
- Medio ambiente y Reserva de Biosfera Seaflower.
- Ciencias del mar.
- Integración fronteriza.
- Trilingüismo.
- Cualquier otra definida por la Junta con base en estudios de
  necesidades del Departamento.

### 2.8 Recursos del Fondo (Art. 4 Ordenanza 007/2025)

- a) Recursos asignados del presupuesto departamental.
- b) Recursos provenientes de entidades públicas del nivel nacional.
- c) Donaciones o aportes de entidades privadas, nacionales e
  internacionales.
- d) Recursos de convenios con organizaciones de cooperación nacional
  e internacional.
- e) Recaudos derivados de créditos no condonables y préstamos
  educativos otorgados (recuperaciones).
- f) Aportes o donaciones de personas naturales (financieros o en
  especie: muebles e inmuebles).

**Aporte mínimo departamental** (Art. 23 Ordenanza 007/2025 y Art. 22
Manual Operativo): **$2.000.000.000 anuales**, de obligatoria inclusión
en el presupuesto de cada vigencia.

### 2.9 Estudio de Costos de Referencia

- **SMLMV** (referencia) ≈ $1.423.500.
- **Beneficio por semestre**: 5 SMLMV = **$7.117.500** por
  beneficiario por semestre.
- **Cobertura inicial estimada**: 28 estudiantes.
- **Semestres máximos por beneficiario**: 10 (5 años).

| Ítem                                              | Valor         |
| ------------------------------------------------- | ------------- |
| Salario mínimo mensual legal vigente (referencia) | $1.423.500    |
| Beneficio económico por semestre (5 SMLMV)       | $7.117.500    |
| Total semestres por beneficiario                  | 10            |
| Total beneficiarios proyectados (presupuesto inicial) | 28         |
| Aporte mínimo departamental anual                 | $2.000.000.000 |

> La plataforma debe permitir actualizar SMLMV, montos y coberturas
> mediante configuración parametrizable.

---

## 3. Glosario Institucional y Abreviaturas

| Término                   | Significado                                                                                  |
| ------------------------- | -------------------------------------------------------------------------------------------- |
| **FODEJAS**               | Fondo para el Desarrollo Educativo de los Jóvenes del Archipiélago.                          |
| **IES**                   | Institución de Educación Superior.                                                           |
| **FUI**                   | Formulario Único de Inscripción.                                                             |
| **JAC / JA**              | Junta de Administración del FODEJAS.                                                         |
| **CT**                    | Comité Técnico del FODEJAS.                                                                  |
| **Coordinación Técnica**  | Coordinación Técnica del FODEJAS (adscrita a la Secretaría de Educación).                    |
| **SMLMV**                 | Salario Mínimo Legal Mensual Vigente.                                                        |
| **OCCRE**                 | Oficina de Control, Circulación y Residencia (tarjeta de residencia).                        |
| **SNIES**                 | Sistema Nacional de Información de la Educación Superior.                                    |
| **SISBÉN**                | Sistema de Identificación de Potenciales Beneficiarios de Programas Sociales.                |
| **MEN**                   | Ministerio de Educación Nacional.                                                            |
| **CPACA**                 | Código de Procedimiento Administrativo y de lo Contencioso Administrativo (Ley 1437/2011). |
| **IPC**                   | Índice de Precios al Consumidor (para actualización monetaria en sanciones).                |
| **Raizal**                | Persona perteneciente al Pueblo étnico Raizal del Archipiélago.                              |
| **Convocatoria Cerrada**  | Convocatoria dirigida a un grupo específico y previamente delimitado (ej. mejores bachilleres / mejores puntajes SABER 11). |
| **Convocatoria Pública**  | Convocatoria abierta a toda la población objetivo.                                           |
| **Pagaré**                | Título valor que firma el beneficiario para garantizar la obligación crediticia.            |
| **Carta de Instrucciones**| Documento donde el beneficiario reconoce obligaciones y autoriza llenar espacios en blanco del pagaré. |
| **Sostenimiento**         | Apoyo económico para manutención, transporte, alojamiento, materiales.                       |
| **Matrícula**             | Valor de los costos académicos certificados por la IES.                                      |

---

## 4. Stack Tecnológico

| Capa                  | Tecnología                                                  |
| --------------------- | ----------------------------------------------------------- |
| **Backend**           | **Django 5.x** (Python 3.12+)                               |
| **API**               | **Django REST Framework (DRF)** + **SimpleJWT**             |
| **Frontend servidor** | **Django Templates** + **HTMX** + **Alpine.js**             |
| **Base de datos**     | **PostgreSQL 16**                                           |
| **Cache / Cola**      | **Redis** + **Celery** (tareas async: correos, jobs batch) |
| **Almacenamiento**    | **S3-compatible** (MinIO en dev) para anexos digitales      |
| **Reportes / PDF**    | **WeasyPrint** (HTML→PDF) para resoluciones y constancias   |
| **Observabilidad**    | **Sentry**, **Prometheus**, **Grafana**                     |
| **CI/CD**             | GitHub Actions + Docker                                     |

> **Decisión explícita**: la plataforma **no se integra** con
> sistemas externos (SNIES, SISBÉN, OCCRE) ni con sistemas bancarios.
> Las verificaciones contra esos sistemas se realizan de manera
> manual/externa y el resultado se registra en la plataforma como
> evidencia. La transacción bancaria se ejecuta en los sistemas del
> Banco; la plataforma únicamente **ordena** el pago.

### 4.1 Principios Arquitectónicos

- **Trazabilidad total**: cada cambio de estado genera un evento
  auditable.
- **Configurabilidad**: las reglas de cada convocatoria (puntajes,
  cupos, fechas, requisitos) son **datos**, no código.
- **Idempotencia** de los procesos críticos.
- **Privacidad por diseño**: minimización de datos y enmascaramiento
  en logs.

---

## 5. Convenciones del Proyecto

### 5.1 Idioma

- **Código**: identificadores en inglés.
- **Mensajes de UI**: en **español**.
- **Documentación**: en **español**.
- **Comentarios de código**: español.

### 5.2 Estilo de Código

- **PEP 8** + **Black** (line-length 100) + **Ruff** + **isort**.
- **Docstrings**: Google style.
- **Tests**: `pytest` + `pytest-django` + `factory_boy`.

### 5.3 Git / Ramas

- `main` — producción.
- `develop` — integración.
- `feat/<id>-<slug>`, `fix/<id>-<slug>`, `chore/<slug>`, `docs/<slug>`.
- **Commits**: Conventional Commits.
- **Squash merge** a `develop` y `main`.

### 5.4 OpenSpec — Estructura del Repositorio

```
.
├── openspec/
│   ├── project.md              # ← este archivo
│   ├── AGENTS.md               # instrucciones operativas para IAs
│   ├── specs/
│   │   └── <capability>/
│   │       └── spec.md         # requisitos actuales (delta neutral)
│   └── changes/
│       ├── <change-id>/
│       │   ├── proposal.md     # por qué y qué cambia
│       │   ├── tasks.md        # plan de implementación
│       │   ├── design.md       # (opcional) decisiones de diseño
│       │   └── specs/...       # deltas propuestos
│       └── archive/            # cambios aplicados o rechazados
```

> Cualquier cambio a las capacidades listadas en la sección 8 debe
> pasar por un `proposal.md` + `tasks.md` + delta en `specs/`.

### 5.5 Datos Sensibles y PII

- Cifrado en reposo (volumen) + TLS 1.2+ en tránsito.
- Política de retención: 20 años para expedientes contractuales
  (pagarés, contratos), conforme a la normatividad archivística
  colombiana.
- **En este `project.md` no se incluyen datos personales de
  beneficiarios ni listados de postulaciones con datos sensibles**;
  esa información se maneja en los sistemas transaccionales con
  los controles de acceso y de PII correspondientes.

---

## 6. Contexto del Dominio — El Fondo FODEJAS

### 6.1 Estructura Orgánica

```
Gobernación del Departamento
├── Gobernador
│   ├── (Delega en Sec. Educación) Ordenación del gasto + Pres. Junta
│   │     → Decreto 0122/2026
│   └── (Delega en Tesorero Gral.)  Manejo de cuentas y pagos
│         → Decreto 0072/2026
├── Secretaría de Educación Departamental
│   ├── Secretario de Educación (Presidente de la Junta)
│   └── Coordinación Técnica del FODEJAS  ← operación diaria
│       └── Comité Técnico (asesor, 5+ miembros)
└── Oficina Jurídica de la Gobernación (2ª instancia en apelaciones)
```

#### 6.1.1 Junta de Administración (Art. 5 Ordenanza 007/2025)

Integrantes con **voz y voto** (excepto el coordinador técnico):

- a) Gobernador del Archipiélago o su delegado — **preside** (hoy,
  delegado en el Secretario de Educación, Decreto 0122/2026).
- b) Alcalde del Municipio de Providencia y Santa Catalina o su
  delegado.
- c) Secretario de Educación Departamental o su delegado.
- d) Un representante de las IES con presencia en el Departamento
  (elegido por ellas).
- e) Un representante del Pueblo étnico Raizal (elegido por la
  Autoridad Raizal, vinculado al sector educativo).
- f) Un representante del sector empresarial aportante al fondo (si
  lo hubiere, seleccionado por la Junta).
- g) Un representante de las acciones comunales (mecanismo
  democrático).
- h) Un representante del Consejo Departamental de Juventudes.

**Secretaría Técnica** (voz, sin voto): el **Coordinador Técnico** del
FODEJAS, designado por el Gobernador.

**Período**: 2 años, reelegibles por un periodo adicional. Se
exceptúan los miembros por razón de su cargo (Gobernador, Alcalde,
Secretario).

**Quórum**: mayoría simple (mitad + 1). Decisiones por mayoría simple.

**Sesiones**: mínimo 2 ordinarias/año. Convocatoria escrita 5 días
hábiles (ordinarias) o 2 días hábiles (extraordinarias). Presenciales
o virtuales. Actas firmadas.

**Conflicto de intereses**: aplica Ley 1952/2019. El miembro debe
declararlo y la mayoría simple aprueba el impedimento; su voto no se
cuenta para ese punto.

#### 6.1.2 Comité Técnico (Art. 6 Decreto 0372/2025)

- **Mínimo 5 miembros** designados por la Junta.
- **No** puede haber superposición con la Junta (separación de
  funciones).
- **Funciones**: evaluar y emitir conceptos técnicos sobre
  solicitudes, proponer lineamientos, hacer seguimiento al
  desempeño académico, asesorar priorización, realizar estudios de
  impacto, sugerir mejoras, elaborar el reglamento interno de
  selección, sesionar trimestralmente (ordinaria) o por convocatoria
  del presidente/mitad+1 (extraordinaria).
- **Recomendaciones no vinculantes**, pero deben ser tenidas en
  cuenta.

#### 6.1.3 Coordinación Técnica (Art. 17 y 18 Manual Operativo)

Adscrita a la Secretaría de Educación. Ejerce como Secretaría
Técnica de la Junta. Funciones por área:

- **Planificación y Gestión Estratégica**:
  - Diseña/actualiza reglamentos operativos.
  - Define criterios de selección, asignación, condonación y
    recuperación.
  - Establece metas anuales.
  - Gestiona convocatorias (planificación, lanzamiento, difusión).
- **Operación y Ejecución**:
  - Recepción, revisión y evaluación de solicitudes.
  - Propuesta de adjudicación a la Junta.
  - **Acompañamiento integral en 3 momentos**:
    1. **Selección** — criterios de valoración del proyecto de vida
       y resiliencia.
    2. **Durante los estudios** — apoyo psicosocial (salud mental,
       manejo de estrés, adaptación académica) para mitigar
       deserción.
    3. **Post-beneficio** — mentoría y orientación vocacional,
       transición al mercado laboral y cumplimiento de retorno.
  - Seguimiento académico (cumplimiento de promedio 3.5).
  - Seguimiento al cumplimiento de compromisos (servicio social o
    retorno).
  - Gestión de desembolsos.
  - Gestión de condonaciones y recuperaciones.
  - Atención y orientación a beneficiarios.
- **Control y Seguimiento Financiero**:
  - Control presupuestal.
  - Informes financieros periódicos.
  - Conciliación trimestral de bases de datos financieras y de
    beneficiarios.
- **Relacionamiento y Comunicación**:
  - Coordinación interinstitucional con IES nacionales e
    internacionales.
  - Informes a la Secretaría de Educación.
  - Difusión externa.
- **Administrativos y Legales**:
  - Documentación y archivo.
  - Atención de casos especiales.
  - Cumplimiento normativo.

#### 6.1.4 Tesorería General (Decreto 0072/2026)

- Maneja y controla la(s) cuenta(s) bancaria(s) del FODEJAS.
- Efectúa pagos a IES y beneficiarios desde sus sistemas bancarios
  (la plataforma **no se integra** con esos sistemas).
- Monitorea ingresos, egresos e inversiones.
- Lleva registros de operaciones de tesorería.
- Verifica cumplimiento de requisitos de los pagos ordenados por la
  plataforma.
- Plazo de pago: **5 días hábiles** tras recibir la documentación
  completa (suspensible por observaciones).
- Procedimiento de pago (Art. 2 Decreto 0072/2026):
  1. Copia del acto administrativo en firme con el listado
     definitivo de beneficiarios.
  2. Carta de autorización de pago/desembolso suscrita por el
     Presidente de la Junta y el Secretario de Educación.
  3. Copia del certificado de cuenta bancaria (sostenimiento) o
     recibo/link de pago de la universidad (matrícula).
  4. Copia del contrato suscrito con el FODEJAS + pagaré + carta
     de instrucciones.

---

## 7. Actores / Roles del Sistema

> La plataforma implementa **RBAC** (Role-Based Access Control) que
> mapea cada rol institucional a permisos específicos. Los permisos
> son granulares a nivel de **convocatoria** y de **etapa del
> proceso**.

### 7.1 Roles de la Plataforma

| Código      | Rol                              | Tipo    | Descripción                                                                                              |
| ----------- | -------------------------------- | ------- | -------------------------------------------------------------------------------------------------------- |
| R-ASPIRANTE | Aspirante                        | Externo | Persona que se inscribe a una convocatoria. Acceso solo a su perfil y sus postulaciones.                |
| R-BENEF     | Beneficiario                     | Externo | Aspirante seleccionado con acto administrativo en firme. Acceso a reportes, condonación y obligaciones. |
| R-COORD     | Coordinador Técnico FODEJAS      | Interno | Opera el día a día. Crea convocatorias, valida requisitos, propone adjudicaciones, sigue beneficiarios.  |
| R-CT        | Miembro del Comité Técnico       | Interno | Emite conceptos técnicos, evalúa postulaciones, propone priorización.                                   |
| R-JUNTA     | Miembro de la Junta              | Interno | Aprueba listados, presupuesto, reglamento, sanciones.                                                  |
| R-PRES      | Presidente de la Junta           | Interno | Firma autorizaciones de pago y preside sesiones. (Típicamente el Secretario de Educación.)              |
| R-SECEDU    | Secretario de Educación          | Interno | Ordenador del gasto delegado. Firma resoluciones y actos administrativos.                               |
| R-TESOR     | Tesorero General                 | Interno | Ejecuta los pagos desde sus sistemas bancarios.                                                        |
| R-OFIJUR    | Oficina Jurídica                 | Interno | Resuelve apelaciones (2ª instancia) y conceptúa actos administrativos.                                   |
| R-CONTROL   | Oficina de Control Interno       | Interno | Auditoría, veedurías, investigaciones disciplinarias internas.                                          |
| R-CIUDA     | Ciudadano (portal público)       | Externo | Acceso a datos abiertos y portal de transparencia (sin autenticación profunda).                         |
| R-ADMIN     | Administrador del sistema        | Interno | Gestión de usuarios, roles, catálogos, configuración global.                                            |
| R-AUDITOR   | Auditor externo / Ente de control| Externo | Acceso de solo lectura a bitácora, reportes y datos para fines de fiscalización.                       |

### 7.2 Mapa Actor × Responsabilidad

| Actividad                                 | R-ASPIR | R-COORD | R-CT | R-JUNTA | R-PRES | R-TESOR | R-OFIJUR | R-CONTROL |
| ----------------------------------------- | :-----: | :-----: | :--: | :-----: | :----: | :-----: | :------: | :-------: |
| Inscribirse                               |    ✓    |         |      |         |        |         |          |           |
| Validar requisitos                        |         |    ✓    |   ✓  |         |        |         |          |           |
| Calificar                                 |         |    ✓    |   ✓  |         |        |         |          |           |
| Aprobar listados                          |         |         |      |    ✓    |        |         |          |           |
| Resolver reclamaciones (1ª inst.)         |         |         |      |    ✓    |        |         |          |           |
| Resolver apelaciones (2ª inst.)           |         |         |      |         |        |         |    ✓     |           |
| Firmar resoluciones                       |         |         |      |         |   ✓    |         |          |           |
| Legalizar crédito (pagaré)                |    ✓    |    ✓    |      |         |        |         |          |           |
| Autorizar pago                            |         |         |      |         |   ✓    |         |          |           |
| Ejecutar pago (desde sistemas bancarios)  |         |         |      |         |        |    ✓    |          |           |
| Seguimiento académico                     |         |    ✓    |   ✓  |         |        |         |          |           |
| Acompañamiento psicosocial                |         |    ✓    |      |         |        |         |          |           |
| Aprobar condonación                       |         |         |      |    ✓    |        |         |          |           |
| Iniciar cobro coactivo                    |         |         |      |    ✓    |        |         |          |           |
| Auditar                                   |         |         |      |         |        |         |          |    ✓      |

---

## 8. Capacidades del Sistema (Catálogo)

> Las capacidades se identifican con un **id estable** (`CAP-NNN`) que
> se reutiliza en `specs/` y `changes/`. La descripción detallada del
> comportamiento de cada capacidad vive en
> `specs/<capability>/spec.md` (no en este archivo).

| ID       | Capacidad                                            | Prioridad |
| -------- | ---------------------------------------------------- | --------- |
| CAP-001  | Autenticación y Gestión de Usuarios/Roles            | P0        |
| CAP-002  | Gestión de Convocatorias (configuración + publicación) | P0      |
| CAP-003  | Inscripción digital (FUI + anexos)                   | P0        |
| CAP-004  | Validación de Requisitos Mínimos                     | P0        |
| CAP-005  | Motor de Calificación y Scoring                      | P0        |
| CAP-006  | Reclamaciones (1ª instancia)                         | P0        |
| CAP-007  | Apelaciones (2ª instancia – Oficina Jurídica)        | P0        |
| CAP-008  | Resultados Definitivos y Acto Administrativo         | P0        |
| CAP-009  | Legalización de Créditos (pagaré, contrato)          | P0        |
| CAP-010  | Autorización y Ejecución de Desembolsos              | P0        |
| CAP-011  | Seguimiento Académico de Beneficiarios               | P1        |
| CAP-012  | Acompañamiento Psicosocial                           | P2        |
| CAP-013  | Incentivos y Condonación Parcial                     | P1        |
| CAP-014  | Condonación Total                                    | P1        |
| CAP-015  | Terminación del Convenio y Causales                  | P0        |
| CAP-016  | Sanciones, Reintegros y Cobro Coactivo               | P0        |
| CAP-017  | Sesiones de Junta y Comité Técnico (actas, votaciones) | P0      |
| CAP-018  | Conflictos de Interés                                | P1        |
| CAP-019  | Notificaciones y Comunicaciones                      | P1        |
| CAP-020  | Reportes de Gestión (trimestrales y anuales)         | P0        |
| CAP-021  | Portal de Transparencia / Datos Abiertos             | P1        |
| CAP-022  | Bitácora de Auditoría (inmutable)                    | P0        |
| CAP-023  | Catálogos Paramétricos                               | P0        |
| CAP-024  | Configuración de Reglas por Convocatoria             | P0        |
| CAP-025  | Protección de Datos Personales (Habeas Data)         | P0        |
| CAP-026  | Manejo de Casos Especiales y Fuerza Mayor            | P1        |
| CAP-027  | Estudio de Impacto                                   | P3        |
| CAP-028  | Auditoría Externa (exportación a entes de control)   | P1        |
| CAP-029  | Firma Electrónica de Documentos                      | P1        |
| CAP-030  | Multidioma y Trilingüismo                            | P3        |

### 8.1 Nota sobre Integraciones Externas

La plataforma **no realiza integraciones automáticas** con sistemas
externos. En particular:

- **SNIES, SISBÉN, OCCRE**: la verificación contra estos sistemas se
  realiza de manera manual o externa. El resultado se registra en la
  plataforma como evidencia (carga de certificado, número de
  consulta, fecha, responsable).
- **Sistemas bancarios**: la plataforma únicamente **ordena** pagos.
  La transacción bancaria se realiza en los sistemas del Banco. La
  plataforma no se integra con APIs bancarias.

---

## 9. Modelo de Dominio

> Modelo lógico de **alto nivel**. Los atributos, validaciones y
> estados detallados de cada entidad se especifican en
> `specs/<capability>/spec.md`. Este `project.md` solo describe las
> entidades y sus relaciones para que cualquier persona pueda
> entender el dominio.

### 9.1 Entidades Principales y Relaciones

```
Persona (1) ──── (N) Postulación (Application) ──── (1) Convocatoria
   │                       │
   │                       ├── (N) Adjunto
   │                       ├── (N) Verificación de Requisito
   │                       ├── (N) Detalle de Calificación
   │                       ├── (0..1) Reclamación ── (0..1) Apelación
   │                       └── (0..1) Beneficio (si es seleccionado)
   │                                    │
   │                                    ├── (N) Legalización
   │                                    ├── (N) Desembolso
   │                                    ├── (N) Seguimiento Académico
   │                                    ├── (N) Acompañamiento Psicosocial
   │                                    └── (0..1) Condonación o Cobro

Convocatoria (1) ──── (1) Configuración (Receta)
Convocatoria (1) ──── (N) Hito de Cronograma
Convocatoria (1) ──── (N) Cupo (por municipio, modalidad, nivel)

Sesión de Junta (1) ──── (N) Punto del Orden del Día (1) ──── (N) Voto
Sesión de Junta (1) ──── (1) Acta
Sesión de Comité Técnico (1) ──── (N) Concepto Técnico

Configuración de Convocatoria (1) ──── (N) Regla de Calificación
```

### 9.2 Entidades

- **Persona**: individuo inscrito o beneficiario, identificado por
  documento de identidad.
- **Convocatoria**: proceso de selección con tipo, periodo, fechas,
  cupos, requisitos y reglas.
- **Configuración de Convocatoria**: "receta" parametrizable que
  define las reglas de una convocatoria concreta.
- **Postulación (Application)**: instancia de inscripción de una
  persona a una convocatoria. Pasa por múltiples estados.
- **Adjunto**: archivo digital asociado a cualquier entidad
  (requisito, postulación, beneficio, sesión, etc.).
- **Verificación de Requisito**: resultado de la validación de cada
  requisito mínimo sobre una postulación.
- **Detalle de Calificación**: desglose del puntaje por criterio.
- **Reclamación** y **Apelación**: recursos administrativos en
  1ª y 2ª instancia.
- **Beneficio**: relación entre un postulante seleccionado y el
  apoyo económico otorgado (modalidad, monto, semestres).
- **Legalización**: documentos contractuales firmados (pagaré,
  carta de instrucciones, contrato).
- **Desembolso**: orden de pago generada por la plataforma y
  ejecutada por la Tesorería en sus sistemas bancarios.
- **Seguimiento Académico**: registros periódicos de promedio y
  estado del beneficiario.
- **Acompañamiento Psicosocial**: registro de intervenciones y
  consentimientos.
- **Condonación** o **Cobro**: cierre del beneficio por graduación
  o por incumplimiento.
- **Sesión de Junta** y **Sesión de Comité Técnico**: reuniones
  formales con orden del día, votaciones y actas.
- **Punto del Orden del Día** y **Voto**: granularidad de la
  decisión colegiada.
- **Acta de Sesión**: documento firmado que soporta lo decidido.
- **Regla de Calificación**: criterio parametrizable de scoring.
- **Hito de Cronograma**: fechas clave de la convocatoria.
- **Cupo**: disponibilidad por municipio, modalidad y nivel.
- **Evento de Auditoría**: registro inmutable de toda acción
  relevante en el sistema.

### 9.3 Reglas de Integridad (alto nivel)

- Una **Persona** puede tener una sola Postulación activa por
  convocatoria, pero puede aparecer en múltiples convocatorias a lo
  largo del tiempo.
- Un **Beneficio** transita por estados de forma monótona creciente,
  salvo suspensiones temporales documentadas (con plazo).
- Un **Desembolso** autorizado pero no pagado tras un período
  definido se marca como vencido y se notifica.
- Los **Eventos de Auditoría** son inmutables: no se eliminan, no se
  modifican.

---

## 10. Flujos de Negocio End-to-End

> Descripción de alto nivel. Los detalles, condiciones de borde y
> excepciones se especifican en `specs/<capability>/spec.md`.

### 10.1 Ciclo General de una Convocatoria

1. **Planeación**: la Coordinación Técnica define tipo, periodo,
   cupos, requisitos, criterios y cronograma.
2. **Aprobación y publicación**: la Junta aprueba las bases y abre
   la convocatoria (acto administrativo).
3. **Inscripción**: las personas radican FUI digital + anexos. El
   sistema asigna radicado.
4. **Verificación de requisitos**: la Coordinación Técnica / CT
   revisa requisitos. Se generan subsanaciones si aplica.
5. **Calificación**: el motor de scoring calcula puntaje y genera
   ranking por municipio.
6. **Resultados preliminares**: se publica el listado preliminar.
7. **Reclamaciones (1ª instancia)**: las personas presentan
   reclamación ante la Junta.
8. **Resultados definitivos**: la Junta resuelve reclamaciones y
   aprueba el listado definitivo.
9. **Apelaciones (2ª instancia)**: las personas pueden apelar ante
   la Oficina Jurídica.
10. **Legalización**: firma de pagaré, carta de instrucciones y
    contrato. Requisito para el primer desembolso.
11. **Desembolsos**: el Presidente de la Junta y el Secretario de
    Educación autorizan; la Tesorería ejecuta el pago en sus
    sistemas bancarios.
12. **Seguimiento académico**: promedio, condicionalidad, retorno,
    aporte. Alertas tempranas.
13. **Condonación o cobro**: al graduarse, condonación total /
    parcial o inicio de cobro coactivo.

### 10.2 Flujo de Inscripción (alto nivel)

La persona:

1. Crea cuenta o inicia sesión.
2. Completa el wizard FUI multi-paso (datos personales,
   verificación de requisitos, información de excelencia, datos de
   educación superior, declaración juramentada).
3. Carga los anexos requeridos.
4. Firma electrónicamente y radica.
5. Recibe comprobante de radicación (número, fecha, hora).

La postulación queda en estado **radicada** y pasa a
verificación.

### 10.3 Flujo de Reclamación / Apelación (alto nivel)

1. La persona insatisfecha con los resultados preliminares
   presenta **reclamación** dentro del plazo.
2. La **Junta** resuelve en 1ª instancia.
3. Si la persona insiste, presenta **apelación** ante la
   **Oficina Jurídica** en 2ª instancia.
4. La Oficina Jurídica emite resolución definitiva.

### 10.4 Flujo de Desembolso (alto nivel)

1. La Coordinación Técnica genera una **orden de pago** por
   beneficiario con los adjuntos normativos.
2. El Presidente de la Junta y el Secretario de Educación
   **autorizan** la orden.
3. La orden se **radica** en Tesorería.
4. La Tesorería **ejecuta el pago** desde sus sistemas bancarios
   (la plataforma no se integra con sistemas bancarios).
5. La Tesorería carga el **comprobante de pago** al sistema.
6. La Coordinación Técnica y la Tesorería realizan
   **conciliación trimestral**.

### 10.5 Flujo de Condonación (alto nivel)

1. La persona beneficiaria se gradúa y carga los documentos
   requeridos.
2. La plataforma valida automáticamente los requisitos de
   condonación.
3. Si cumple: la Junta aprueba la condonación.
4. Si no cumple: se inicia el flujo de cobro o de condonación
   parcial, o se evalúa una solicitud de exoneración por fuerza
   mayor.

---

## 11. Reglas de Negocio Críticas

### 11.1 Requisitos Mínimos (Art. 11 Decreto 0372/2025)

| # | Requisito                                                                                                | Medio de verificación                                                                                              | Responsable de verificación |
| - | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | --------------------------- |
| 1 | Ser egresado de una IE del Archipiélago (a partir de 2023 para la convocatoria cerrada de excelencia).  | Diploma o acta de grado; acto administrativo de "mejor bachiller / 10 mejores SABER 11".                            | Junta de Administración     |
| 2 | Pertenecer a los estratos 1, 2, 3 o a los grupos SISBÉN A, B, C.                                         | Certificación SISBÉN o Secretaría de Planeación.                                                                    | Junta                       |
| 3 | Pertenecer a la etnia Raizal o ser residente del Archipiélago.                                           | Copia de la tarjeta de residencia OCCRE.                                                                           | Junta                       |
| 4 | Estar admitido o estudiando pregrado (técnico/tecnológico/universitario) en IES colombiana (púb./priv.). | Orden de matrícula o certificado de admisión (periodo vigente).                                                   | Junta                       |
| 5 | Contar con cuenta bancaria activa en Colombia.                                                            | Certificación bancaria con fecha ≤ 30 días calendario previos a la apertura.                                       | Junta                       |
| 6 | No contar con título profesional universitario.                                                          | Consulta SNIES (manual/externa, registrada como evidencia en la plataforma).                                       | Junta                       |
| 7 | Si está cursando: promedio mínimo 3.5.                                                                    | Certificado de notas de la universidad.                                                                            | Junta                       |

**Reglas derivadas**:

- Documentos con inconsistencias o presuntas adulteraciones ⇒
  suspensión del proceso con el beneficiario hasta verificar
  veracidad.
- No estar recibiendo beneficios similares para los mismos rubros de
  otra entidad departamental/nacional/internacional.

### 11.2 Población Objetivo y Priorización

**Habilitados** (Art. 9 Ordenanza 007/2025):

- a) Egresados de IE del Archipiélago con situación de residencia
  conforme al Decreto 2762 de 1991.
- b) Personas del grupo étnico Raizal en vulnerabilidad económica.
- c) Proyección social, liderazgo comunitario o compromiso
  territorial.
- d) Deportistas destacados (avalados por la Liga).
- e) Personas en situación de discapacidad, víctimas del conflicto
  armado, desplazamiento forzado, comunidades rurales
  (certificación autoridad competente).

**Prioridad** (Art. 8 Manual Operativo, Art. 11 Ordenanza 007):

1. Estudiantes de instituciones públicas.
2. Víctimas del conflicto armado (reparación colectiva del Pueblo
   Raizal).
3. Personas en situación de discapacidad.
4. Pertenecientes al Grupo Étnico Raizal.
5. Mejores puntajes de instituciones oficiales y privadas (estratos
   1, 2, 3).
6. Alto rendimiento académico.
7. Deportistas destacados.

### 11.3 Criterios de Calificación

Configuración por defecto (alineada con la convocatoria cerrada de
ejemplo):

| Criterio                             | Ponderación | Medio de verificación                                |
| ------------------------------------ | ----------- | ----------------------------------------------------- |
| I. Mérito Académico                  | 50 pts      | Acto administrativo (mejor bachiller / 10 mejores).  |
| II. Condición Socioeconómica         | 30 pts      | SISBÉN (A, B, C) o Planeación (estratos 1, 2, 3).    |
| III. Pertenencia Étnica y Residencia | 20 pts      | OCCRE.                                                |
| **Total**                            | **100 pts** |                                                       |

> Esta configuración es la base de la convocatoria de
> Reconocimiento a la Excelencia. La plataforma debe permitir
> variantes en futuras convocatorias.

### 11.4 Duración y Monto del Beneficio

- **Modalidad principal**: Crédito Educativo Condonable. También
  aplica Beca o Préstamo no condonable.
- **Duración máxima**: 5 años (10 semestres académicos), según
  plan de estudios oficial, o el tiempo restante si ya está en
  curso.
- **Monto por semestre**: 5 SMLMV (configurable).
- **Plazos máximos por nivel** (Art. 16 Decreto 0372/2025):
  - Técnico profesional: 3 años.
  - Tecnológico: 4 años.
  - Profesional pregrado: 6 años.
  - Especialización y Maestría: 2 años.
  - Doctorado: 5 años.

### 11.5 Regla de Excepción para Providencia Isla

> Si el mejor puntaje SABER 11 o mejor bachiller de Providencia Isla
> ya cuenta con un beneficio similar activo de otra entidad, el
> cupo se asigna **automáticamente al segundo mejor puntaje** del
> municipio, siempre que cumpla con los demás requisitos y
> criterios de priorización.

**Implicación**: el motor de calificación y asignación de cupos
debe permitir reglas municipales especiales parametrizadas por
convocatoria.

### 11.6 Causales de Terminación

**Terminación del convenio** (Art. 14 Decreto 0372/2025):

1. Abandono injustificado.
2. Retiro voluntario.
3. Finalización de periodos financiados.
4. Adulteración o información falsa.
5. Sanción disciplinaria/académica de la IES.
6. Promedio < 3.5 acumulado.
7. Muerte.

**Terminación de desembolsos** (Art. 15 Decreto 0372/2025) — incluye
las anteriores más:

- 2 semestres consecutivos de suspensión.
- No renovación o aplazamiento por más de 2 periodos académicos.
- No alcanzar el promedio por más de 2 periodos académicos.
- La Junta puede autorizar **suspensiones temporales adicionales
  hasta 4 semestres** por fuerza mayor o caso fortuito.

### 11.7 Sanciones y Reintegros (Art. 17 Decreto 0372/2025)

- **Sanción**: reembolso total de los recursos otorgados +
  actualización por IPC.
- **Justificaciones válidas**:
  - Enfermedad grave certificada.
  - Accidente con afectación significativa.
  - Emergencia familiar.
  - Traslado definitivo fuera del país.
- **Procedimiento**: solicitud formal a la Junta con soportes →
  resolución motivada en 30 días calendario → apelación ante
  Oficina Jurídica.
- **Fallecimiento**: la deuda cesa automáticamente.

### 11.8 Conflicto de Intereses (Art. 14 Manual Operativo)

- Aplican las inhabilidades e incompatibilidades de la Constitución
  y la Ley 1952/2019.
- Declaración obligatoria previa a cada punto del orden del día.
- Aprobación del impedimento por mayoría simple; el voto no cuenta
  para ese punto.

### 11.9 Garantías (Art. 24 Manual Operativo)

- **Pagaré con espacios en blanco**: compromiso de reintegro si se
  cumplen las condiciones.
- **Carta de Instrucciones**: aceptación de obligaciones y
  autorización para llenar espacios en blanco.
- La Junta puede establecer garantías adicionales.

### 11.10 Contratación y Forma de Entrega (Art. 20 Ordenanza 007/2025)

> *"Los recursos que serán entregados a los beneficiarios de becas,
> préstamos condonables y no condonables serán entregados
> directamente a la entidad educativa donde estudiará el
> beneficiado. El Gobierno Departamental realizará las gestiones
> para que el estudiante ingrese a la universidad en el primer
> semestre del año lectivo."*

**Implicación**: en la mayoría de los casos el pago se hace a la
IES (matrícula). Solo sostenimiento se paga al beneficiario (cuenta
de ahorros). **La transacción bancaria la ejecuta la Tesorería
desde sus sistemas; la plataforma no se integra con sistemas
bancarios**.

### 11.11 Asignación de Recursos (Art. 23 Ordenanza 007/2025)

- 80% pregrado.
- 20% maestrías y doctorados (áreas de alta demanda insular, en
  territorio nacional y en el exterior).

### 11.12 Cobertura Geográfica Equitativa (Art. 15 Ordenanza 007/2025)

> *"Diseñar estrategias que aseguren la representación lo más
> equitativamente posible para todas las comunidades de la Sociedad
> Isleña, así como del Pueblo étnico Raizal del Archipiélago frente
> a la correspondiente asignación financiera, acceso y distribución
> de las becas, permanencia y graduación."*

---

## 12. Convocatoria de Referencia — Cerrada "Reconocimiento a la Excelencia" 2026-1

> Documento normativo que **ejemplifica** el ciclo completo. La
> plataforma debe ser capaz de configurar y ejecutar esta
> convocatoria sin código nuevo.

### 12.1 Datos Generales

- **Nombre**: LINEAMIENTOS Y TÉRMINOS DE REFERENCIA PARA LA
  SELECCIÓN DE BENEFICIARIO PRIMERA CONVOCATORIA CERRADA DEL
  FODEJAS — RECONOCIMIENTO A LA EXCELENCIA.
- **Periodo**: Primer semestre de 2026-1.
- **Población objetivo**: las 10 mejores en Pruebas Saber 11 y
  mejores bachilleres de cada IE pública o privada de estratos 1,
  2, 3 del Departamento.
- **Modalidad**: Crédito Educativo Condonable.
- **Monto**: 5 SMLMV semestrales (matrícula o sostenimiento, a
  elección del beneficiario).
- **Duración**: hasta 5 años (10 semestres).

### 12.2 Cronograma (referencia)

| #  | Etapa                                              | Responsable                       | Inicio       | Cierre       |
| -- | -------------------------------------------------- | --------------------------------- | ------------ | ------------ |
| 1  | Publicación de la convocatoria y bases            | Sec. Educación / Coord. Técnica   | 12/11/2025   | 15/11/2025   |
| 2  | Periodo de inscripción (recepción de FUI y docs)   | Aspirante                         | 17/11/2025   | 28/11/2025   |
| 3  | Verificación de requisitos y calificación         | Sec. Educación / Coord. / CT      | 1/12/2025    | 5/12/2025    |
| 4  | Publicación de resultados preliminares             | Sec. Educación / Coord.           | 9/12/2025    | 12/12/2025   |
| 5  | Reclamaciones (1ª inst. – Junta)                  | Aspirante                         | 9/12/2025    | 12/12/2025   |
| 6  | Respuesta a reclamaciones y resultados definitivos | Junta                             | 15/12/2025   | 19/12/2025   |
| 7  | Apelaciones (2ª inst. – Oficina Jurídica)          | Aspirante                         | 15/12/2025   | 19/12/2025   |
| 8  | Legalización (firma de pagarés)                   | Beneficiario + acudiente          | 5/01/2026    | 9/01/2026    |
| 9  | Autorización y ejecución de desembolsos            | Junta / Sec. Hacienda             | 5/01/2026    | 9/01/2026    |

### 12.3 Estructura del FUI (digital)

- **Datos del Aspirante**: nombres, documento, fecha y lugar de
  nacimiento, dirección Archipiélago, contacto, correo.
- **Verificación de Requisitos Mínimos** (7 booleans con
  adjuntos).
- **Información Académica y de Excelencia**:
  - IE de egreso (pública/privada), año de graduación.
  - Marcaje único: Mejor Bachiller **o** 10 mejores SABER 11.
  - Soporte: acto administrativo o certificación oficial.
  - Datos de educación superior: programa, nivel, IES, modalidad,
    promedio.
- **Declaración y Compromiso** (firma electrónica, huella
  dactilar opcional).

### 12.4 Listado de Beneficiarios

> ⚠️ Por política de protección de datos personales, este
> `project.md` **no incluye** datos personales de los
> beneficiarios de la convocatoria (nombres, documentos, IES
> puntual, modalidad asignada). Esa información se gestiona en
> los sistemas transaccionales de la plataforma con los
> controles de acceso y de PII correspondientes, y se publica
> únicamente a través de los **actos administrativos** y el
> **portal de transparencia** (CAP-021) en formatos que
> cumplen la Ley 1581 de 2012.

---

## 13. Seguridad, Auditoría y Cumplimiento

### 13.1 Autenticación y Autorización

- **Django Auth** con contraseñas hasheadas (PBKDF2/Argon2).
- **JWT** (SimpleJWT) para integraciones.
- **MFA** (TOTP) para roles internos.
- RBAC con permisos granulares por convocatoria y etapa.

### 13.2 Protección de Datos Personales

- Cumplimiento de la **Ley 1581/2012** y el **Decreto
  1377/2013**.
- Registro de tratamiento de datos publicado.
- Captura de **consentimiento expreso, informado e inequívoco**
  al momento de la inscripción.
- **Habeas data**: módulo de solicitudes de consulta,
  rectificación, actualización y supresión.
- **Enmascaramiento de PII** en logs y reportes públicos.

### 13.3 Bitácora de Auditoría

- Tabla append-only con **encadenamiento de hashes** (cada evento
  contiene el hash del anterior).
- Captura: timestamp UTC, actor, acción, entidad, id,
  antes/después (resumen), IP, user-agent, módulo.
- Retención: 20 años.
- Exportación a entes de control.

### 13.4 Cumplimiento CPACA (Ley 1437/2011)

- Notificación personal, por aviso, o por edicto, según aplique.
- Términos para recursos y apelaciones.
- Corrección de errores formales (art. 45 CPACA).
- Numeración y fecha de actos administrativos.

### 13.5 Roles y Segregación de Funciones

- Quien autoriza no ejecuta; quien ejecuta no autoriza; quien
  audita no opera.
- Cuatrovíos: nunca el mismo usuario puede crear + aprobar +
  ejecutar pago sobre el mismo desembolso.

### 13.6 Canales de Denuncia (Art. 20.d Manual Operativo)

- Módulo de "Reportar irregularidad" en el portal.
- Investigación confidencial por la Oficina de Control Interno.
- Sanciones administrativas, disciplinarias y penales si aplica.

---

## 14. Reportes y Transparencia

### 14.1 Informes Internos (R-COORD, R-JUNTA, R-SECEDU)

- **Ejecución presupuestal** (mensual / trimestral).
- **Beneficiarios por cohorte / convocatoria / municipio / IES /
  modalidad / nivel** (agregados, no listados nominales).
- **Estado de seguimiento académico** (al día / en riesgo /
  suspendido / terminado).
- **Pagos pendientes, en proceso y pagados**.
- **Tasa de graduación**, **tasa de retorno**, **tasa de aporte
  comunitario**.

### 14.2 Informes Públicos (R-CIUDA)

- Convocatorias abiertas y cerradas.
- Calendario de próximas aperturas.
- Estadísticas agregadas de beneficiarios (sin datos
  personales).
- Montos girados por año / IES / municipio (agregados).
- Estadísticas de impacto (bianual, Art. 20.f Manual Operativo).

### 14.3 Exportación para Entes de Control (R-AUDITOR)

- Formato CSV y JSONL.
- Conjuntos de datos alineados con los reportes de la
  Gobernación.
- Sellado de tiempo + firma.

---

## 15. Supuestos, Restricciones y Alcance

### 15.1 Supuestos

- El proceso de **pago se realiza en los sistemas bancarios del
  Banco**, no en la plataforma; la plataforma ordena, no
  ejecuta. **No existe integración con sistemas bancarios**.
- **No existe integración automática con SNIES, SISBÉN ni
  OCCRE**. La verificación contra estos sistemas se realiza de
  manera manual o externa; el resultado se registra en la
  plataforma como evidencia (carga de documento, número de
  consulta, fecha, responsable).
- La **firma electrónica** debe ser jurídicamente válida en
  Colombia (Ley 527/1999 y Decreto 2364/2012).
- Los datos migrados desde el proceso actual son: padrones, FUI
  físicos escaneados, resoluciones previas.
- El **Pueblo étnico Raizal** debe tener representación
  diferenciada en UI y reportes.

### 15.2 Restricciones

- El sistema opera en horario 7×24, pero con ventanas de
  mantenimiento en horas no hábiles.
- Las convocatorias tienen **plazos improrrogables** ("la no
  radicación de documentos en las fechas establecidas será
  causal de rechazo").
- Datos sensibles: cualquier publicación pública requiere
  agregación y anonimización.
- Lenguaje claro: las plantillas de comunicación deben ser
  comprensibles para poblaciones diversas (alfabetización
  variable, segunda lengua).

### 15.3 Riesgos Conocidos

| #  | Riesgo                                                                                     | Mitigación                                                                  |
| -- | ------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------- |
| R1 | Cambios en la verificación manual de SNIES/SISBÉN/OCCRE (procesos lentos o no disponibles). | Plazos claros de subsanación; evidencia registrada en la plataforma.        |
| R2 | Adulteración de documentos o suplantación.                                                  | Firma electrónica + hash + verificación contra autoridad competente.        |
| R3 | Cambios regulatorios (CPACA, Habeas Data, etc.).                                           | OpenSpec permite actualizar specs sin redeploy completo.                    |
| R4 | Falla de procesos bancarios externos.                                                      | Reintento manual desde Tesorería; transacciones idempotentes en la plataforma. |
| R5 | Captura de datos en zonas sin conectividad.                                                 | Radicación presencial conservada como opción.                              |
| R6 | Sobrecarga de la Coordinación Técnica en momentos pico.                                   | Batch processing, UI con asistente, plantillas prediseñadas.               |
| R7 | Resistencia al cambio por parte de usuarios institucionales.                                | Plan de cambio + capacitación + manuales.                                  |
| R8 | Pérdida de trazabilidad por mal uso.                                                       | Bitácora inmutable + alertas de comportamiento anómalo.                     |
| R9 | Filtración de datos personales.                                                            | Mínimo privilegio, cifrado, DLP, pruebas de seguridad periódicas.          |

---

## 16. Referencias Normativas

1. **Ordenanza Departamental No. 007 de 2025** (29 de abril de
   2025) — *"Por medio del cual se crea el Fondo para el
   Desarrollo Educativo de los Jóvenes del Archipiélago para la
   Educación Superior de San Andrés, Providencia y Santa
   Catalina y se establecen políticas públicas para su
   funcionamiento."*

2. **Decreto Departamental No. 0372 de 2025** (12 de agosto de
   2025) — *"Por el cual se reglamenta la Ordenanza 007 del 29
   de abril de 2025 para la creación del Fondo para el
   Desarrollo Educativo de los Jóvenes del Archipiélago para la
   Educación Superior de San Andrés, Providencia y Santa
   Catalina y se dictan otras disposiciones."*

3. **Manual Operativo del FODEJAS** — Anexo integral del
   Decreto 0372/2025.

4. **Decreto Departamental No. 0072 de 2026** (09 de febrero
   de 2026) — *"Por el cual se asignan unas funciones y se
   adoptan otras disposiciones"* (Tesorero General del
   Departamento).

5. **Decreto Departamental No. 0122 de 2026** (06 de marzo de
   2026) — *"Por medio del cual se delegan unas funciones en
   el Secretario de Educación del Departamento Archipiélago de
   San Andrés, Providencia y Santa Catalina."*

6. **Resolución Departamental No. 000564 del 30 de enero de
   2026** — Listado definitivo de beneficiarios de la
   Convocatoria Pública 001-2025.

7. **Resolución Departamental No. 0014 de 2026** (19 de febrero
   de 2026) — Corrección del artículo 2° de la Resolución
   000564/2026.

8. **Términos de Referencia — Primera Convocatoria Cerrada del
   FODEJAS — Reconocimiento a la Excelencia, Primer Semestre
   2026-1**.

9. **Formulario Único de Inscripción (FUI)** — Modelo físico
   base para la versión digital.

10. **Ordenanza Departamental No. 005 de 2024** (31 de mayo) —
    Plan de Desarrollo Departamental 2024-2027 "El Archipiélago
    Avanza".

11. **Marco legal nacional** referenciado en §2.1.1.

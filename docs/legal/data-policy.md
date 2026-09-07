# Política de datos

## Principio

Gasto Abierto Bolivia solo procesa **información pública** publicada por fuentes oficiales o repositorios de datos abiertos.

## Permitido

- Presupuestos y ejecución publicados en portales oficiales
- Procesos de contratación SICOES y datasets OCDS/CSV de datos.gob.bo
- Metadatos de informes de auditoría de la Contraloría (título, entidad, año, URL pública)
- PDFs de rendición de cuentas municipales/departamentales publicados en sitios oficiales

## Prohibido en este proyecto

- Declaraciones juradas de bienes con detalle patrimonial no publicado libremente (DJBR con login/CAPTCHA)
- Datos tributarios individuales reservados
- Credenciales, captchas resueltos de forma abusiva, o bypass de autenticación
- Datos personales sensibles más allá de lo estrictamente publicado para fiscalización (nombres de funcionarios en informes públicos sí; domicilios privados no)

## Licencias

- Código: Apache-2.0
- Datasets de datos.gob.bo: respetar la licencia indicada en cada package (p.ej. CC-BY-SA / licencia Bolivia) y atribuir la fuente
- Cada ficha en `docs/sources/` documenta atribución y rate limit

## Scraping ético

- Revisar `robots.txt` cuando exista
- Rate limit ≤ 1 petición/segundo por defecto
- Almacenar raw para auditoría y re-parseo sin re-golpear el origen
- Preferir APIs/datasets abiertos cuando existan

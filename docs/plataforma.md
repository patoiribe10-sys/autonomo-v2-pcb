# Plataforma de documentación

Para documentar esta placa se recomienda, y se usó, un repositorio de Git con archivos Markdown publicado como sitio estático en GitHub Pages. Es el mismo enfoque del sitio de referencia de la clase, que hace lo propio en Bitbucket.

## Qué se le pide a la plataforma

Una PCB genera archivos de varios tipos (PDF, Gerbers, hojas de cálculo, código) y cambia con el tiempo. La documentación tiene que:

1. Vivir junto a los archivos de diseño, para que no se separen.
2. Guardar historial: qué cambió, cuándo y por qué.
3. Leerse desde cualquier navegador, sin instalar nada ni pedir permiso.
4. Poder editarse con un editor de texto cualquiera.
5. No costar.

## Comparación

| Opción | Junto a los archivos | Historial | Lectura sin cuenta | Costo | Comentario |
|---|---|---|---|---|---|
| **Repositorio Git + Markdown + Pages** | Sí | Completo, por cambio | Sí | Gratis en repositorios públicos | La opción elegida |
| Wiki del repositorio | A medias | Sí | Sí | Gratis | Práctica para notas, pero queda separada del código y de los archivos |
| MkDocs o Docusaurus | Sí | Completo | Sí | Gratis | Mejor buscador y temas, a cambio de un paso de compilación |
| Notion o Confluence | No | Limitado | Depende del plan | De pago para equipos | Cómodas para escribir; los archivos de diseño quedan en otro lado |
| Documento de Word o PDF | No | Solo por copias | Hay que mandarlo | Gratis | Bueno como entrega formal, malo como documentación viva |
| Google Docs | No | Por documento | Con liga | Gratis | Sirve para borradores en equipo |

## Por qué Git con Markdown

- **Un solo lugar.** El esquemático, los Gerbers, el BOM, el firmware de prueba y el texto que los explica están en el mismo repositorio. Quien lo clona se lleva todo.
- **Historial real.** Cada cambio queda con fecha, autor y mensaje. Cuando lleguen las mediciones de la placa, el cambio en la documentación queda registrado junto con cualquier corrección al diseño.
- **Markdown se lee en cualquier parte.** GitHub muestra los `.md` ya con formato, así que la documentación se puede leer aunque el sitio no esté publicado.
- **Sin compilación.** El sitio es una página que carga los Markdown directamente. Editar un archivo y subirlo es todo el proceso de publicación.
- **Así se trabaja afuera.** El sitio de referencia de la clase, de una tarjeta de evaluación comercial, está hecho de esta forma. Conocer el flujo sirve más allá de esta materia.

## GitHub o Bitbucket

Las dos plataformas hacen lo mismo para este fin. Se eligió GitHub porque el equipo ya tiene ahí sus cuentas y es donde va a quedar el código del carro. Si la clase pidiera Bitbucket, el contenido se pasa sin cambios: son los mismos archivos.

## Cómo está organizado este repositorio

| Carpeta | Contenido |
|---|---|
| `docs/` | Las páginas en Markdown, una por tema |
| `hardware/` | Esquemático, Gerbers, BOM, plano y proyecto de Altium |
| `firmware/` | Firmware de prueba |
| `assets/` | Imágenes, estilos y el script del sitio |
| `index.html` | Página que arma el sitio a partir de `docs/` |

## Recomendaciones para mantenerla

- Actualizar la página y el archivo de diseño en el mismo cambio.
- Poner fecha a todo lo que sea un estado ("al 12 de noviembre…"), para que se note cuando envejece.
- Marcar con claridad qué está medido y qué es solo cálculo.
- Guardar las imágenes generadas, no capturas de pantalla sueltas, para poder rehacerlas.

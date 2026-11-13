# Archivos de diseño

Todo lo necesario para revisar, fabricar o modificar la placa está en la carpeta [`hardware/`](https://github.com/patoiribe10-sys/autonomo-v2-pcb/tree/main/hardware) del repositorio.

## Documentación

| Archivo | Contenido |
|---|---|
| [Autonomo_V2_esquematico.pdf](../../hardware/Autonomo_V2_esquematico.pdf) | Esquemático completo, vectorial y con búsqueda |
| [Plano_PCB_Autonomo_V2_soporte.pdf](../../hardware/Plano_PCB_Autonomo_V2_soporte.pdf) | Plano acotado de la placa y sus barrenos |
| [PCB_Autonomo_V2_agujeros_M3.dxf](../../hardware/PCB_Autonomo_V2_agujeros_M3.dxf) | Contorno y barrenos M3 para diseñar el soporte en CAD |

## Fabricación

| Archivo | Contenido |
|---|---|
| [Autonomo_V2_gerber_drill_4capas.zip](../../hardware/Autonomo_V2_gerber_drill_4capas.zip) | Gerbers de las cuatro capas, máscara, pasta, serigrafía, contorno y archivos de barrenado |
| [Autonomo_V2_BOM_CPL.xlsx](../../hardware/Autonomo_V2_BOM_CPL.xlsx) | Lista de materiales y, en otra hoja, la posición de cada pieza |
| [Autonomo_V2_CPL.csv](../../hardware/Autonomo_V2_CPL.csv) | Pick and place: coordenadas en mm con origen en la esquina inferior izquierda |

**Contenido del zip de Gerbers:**

| Extensión | Capa |
|---|---|
| GTL, G1, G2, GBL | Cobre: L1, L2 (GND), L3 (potencia), L4 |
| GTS, GBS | Máscara superior e inferior |
| GTP, GBP | Pasta |
| GTO, GBO | Serigrafía |
| GM | Contorno de la placa |
| TXT | Barrenos redondos metalizados y sin metalizar, y ranuras |

Al pedir una placa de 4 capas hay que indicarle al fabricante el orden: L1 GTL, L2 G1, L3 G2, L4 GBL.

## Fuentes

| Archivo | Contenido |
|---|---|
| [Proyecto_Alain_Altium.zip](../../hardware/Proyecto_Alain_Altium.zip) | Proyecto completo de Altium Designer 26: `Proyecto_Alain.PrjPcb`, `Autonomo_V2.SchDoc`, `Autonomo_V2.PcbDoc`, las librerías de cada pieza y las salidas |

## Firmware

| Archivo | Contenido |
|---|---|
| [`firmware/prueba-pcb/`](https://github.com/patoiribe10-sys/autonomo-v2-pcb/tree/main/firmware/prueba-pcb) | Proyecto de PlatformIO con el firmware de prueba de la placa |

## Cómo se generó cada cosa

| Salida | Herramienta |
|---|---|
| Esquemático en PDF | Smart PDF de Altium |
| Gerbers y barrenos | Fabrication Outputs de Altium, en mm, formato 4:4 |
| BOM y CPL | Exportados de Altium y acomodados al formato de PCBWay |
| Imágenes de capas de este sitio | Generadas a partir de los mismos Gerbers que se mandaron a fabricar |
| Vista superior 3D | Captura del modo 3D de Altium |

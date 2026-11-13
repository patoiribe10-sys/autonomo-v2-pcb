# PCB Autonomo_V2

Documentación de la placa de control del carro autónomo a escala 1:10 del equipo DELTA (Universidad Anáhuac Querétaro) para la categoría de conducción urbana de RoboUAQ.

**Sitio:** https://patoiribe10-sys.github.io/autonomo-v2-pcb/

![Vista superior de la placa](assets/img/pcb-top.png)

La placa recibe una batería LiPo 3S, genera 10 V para una Jetson Orin Nano, 5 V para la lógica, 5 V aparte para el servo y 3.3 V, y lleva un ESP32-WROOM-32E que controla el motor y la dirección. Son 4 capas en 100 × 100 mm, diseñada en Altium Designer y fabricada con ensamblaje en PCBWay.

## Contenido

| Tema | Página |
|---|---|
| Diagrama Top-Level | [docs/sistema/top-level.md](docs/sistema/top-level.md) |
| Diagrama de funcionamiento del sistema | [docs/sistema/funcionamiento.md](docs/sistema/funcionamiento.md) |
| Esquemático | [docs/hardware/esquematico.md](docs/hardware/esquematico.md) |
| Diseño de la PCB | [docs/hardware/pcb.md](docs/hardware/pcb.md) |
| Ubicación de componentes | [docs/hardware/README.md](docs/hardware/README.md) |
| Componentes principales | [docs/hardware/componentes.md](docs/hardware/componentes.md) |
| Lista de materiales (BOM) | [docs/hardware/bom.md](docs/hardware/bom.md) |
| Diagrama de alimentación | [docs/hardware/alimentacion.md](docs/hardware/alimentacion.md) |
| Pines de salida (Pinout) | [docs/hardware/pinout.md](docs/hardware/pinout.md) |
| Conectividad (USB y Bluetooth) | [docs/hardware/conectividad.md](docs/hardware/conectividad.md) |
| Fotografía del resultado final | [docs/resultado.md](docs/resultado.md) |
| Guía de usuario | [docs/guia/README.md](docs/guia/README.md) |
| Recomendación de plataforma para documentación | [docs/plataforma.md](docs/plataforma.md) |

## Carpetas

| Carpeta | Contenido |
|---|---|
| `docs/` | Documentación en Markdown |
| `hardware/` | Esquemático en PDF, Gerbers, BOM, CPL, plano mecánico y proyecto de Altium |
| `firmware/prueba-pcb/` | Firmware de prueba (PlatformIO) |
| `assets/` | Imágenes y archivos del sitio |
| `reporte/` | Reporte formal y presentación |

## Ver el sitio en tu computadora

El sitio es estático. Desde la carpeta del repositorio:

```
python -m http.server 8000
```

y abre `http://localhost:8000`.

## Estado

Diseño terminado y en fabricación (noviembre de 2026). Las mediciones de la placa real se agregarán en [docs/resultado.md](docs/resultado.md) cuando llegue.

## Autor

Alain Iribe Haddad · Ingeniería Mecatrónica, Universidad Anáhuac Querétaro · Equipo DELTA

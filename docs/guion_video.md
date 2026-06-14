# Guión — Video Demostrativo TAI (Sistema Experto)

**Duración estimada:** 8–10 minutos  
**Herramienta:** OBS Studio o cualquier grabador de pantalla  
**Lo que se ve en pantalla:** se indica entre corchetes `[PANTALLA]`

---

## PARTE 1 — Introducción (0:00 – 1:00)

`[PANTALLA: Portada con el nombre del proyecto, tu nombre y materia]`

> "Hola, mi nombre es Alvaro Ortiz, estudiante del CETI Colomos, grupo 7E.
> En este video voy a presentar mi proyecto final de Sistemas Expertos:
> **TAI, Asesor de Negocios con Inteligencia Artificial**, un bot de Discord
> que simula la gestión económica de una cafetería de especialidad
> en Guadalajara, Jalisco."

> "El sistema funciona como un **sistema experto**: tiene una base de
> conocimiento con reglas IF-THEN, un motor de inferencias que razona
> sobre el estado del negocio, y tres agentes especializados que trabajan
> juntos para dar retroalimentación al usuario en tiempo real."

---

## PARTE 2 — Explicación del proyecto (1:00 – 2:30)

`[PANTALLA: Prototipo Figma — https://gown-kinder-24829009.figma.site/]`

> "La idea del proyecto es que cualquier persona pueda abrir este bot en
> Discord y simular cómo operaría su propia cafetería en la ZMG, eligiendo
> la zona donde quiere ubicarse: desde el Centro Histórico hasta Andares
> o la periferia. Cada zona tiene multiplicadores diferentes de renta
> y de demanda."

> "El sistema modela costos reales en pesos mexicanos: renta, nómina de
> barista, servicios, grano —comercial o de especialidad de Chiapas o
> Veracruz—, leche, vasos y una merma del 7.5 por ciento.
> El precio de referencia del mercado en Guadalajara es de 55 pesos por taza."

`[PANTALLA: Repositorio GitHub — github.com/Ortiz-Ascencio-Alvaro-Martin/SE-Discord]`

> "Todo el código fuente está disponible en este repositorio de GitHub."

---

## PARTE 3 — Arquitectura del sistema (2:30 – 4:00)

`[PANTALLA: Diagrama de arquitectura del PDF — abre docs/GG_registro_Proy.pdf, página de arquitectura]`

> "La arquitectura se divide en tres capas."

> "Primero, la **capa de presentación**: el usuario interactúa con slash
> commands de Discord, botones y menús desplegables. El bot responde
> con embeds que cambian de color según el estado financiero: verde
> si el flujo neto es positivo, amarillo si hay pérdida leve, y rojo
> si la situación es crítica."

> "En el centro está la **capa de lógica**, organizada en el paquete `core`:
> el módulo de economía con las fórmulas puras, el motor de reglas IF-THEN,
> el motor de eventos macroeconómicos, y los tres agentes."

> "En la base está la **capa de datos**: una base de datos SQLite con
> cinco tablas. La más importante es `registro_inferencias`, que guarda
> cada decisión que tomó el sistema con su justificación en lenguaje natural.
> Eso es lo que hace al sistema explicable."

---

## PARTE 4 — Los tres agentes (4:00 – 5:30)

`[PANTALLA: Archivo core/agentes.py abierto en el editor]`

> "El sistema tiene tres agentes con responsabilidades claramente separadas."

> "El **Agente 1, de Atención**, interpreta lo que el usuario quiere hacer.
> Recibe el comando o el texto y lo convierte en una intención estructurada:
> avanzar ciclo, comprar insumos, ajustar precio. Es el único punto de
> contacto con Discord."

> "El **Agente 2, de Pedido e Inferencia**, es el núcleo del sistema experto.
> Cuando el usuario avanza un ciclo, este agente hace nueve pasos:
> obtiene el inventario, calcula el costo variable real según el tipo de
> grano y leche, genera un evento macroeconómico aleatorio, aplica su
> impacto, calcula la demanda con elasticidad precio, evalúa las cuatro
> reglas IF-THEN, resuelve el ciclo económico, persiste todo en la base
> de datos, y consume el inventario con merma."

> "El **Agente 3, Supervisor**, es el responsable de la explicabilidad.
> Lee el registro de inferencias de ese ciclo y genera una explicación
> en lenguaje natural que le dice al usuario por qué el sistema tomó
> cada decisión. Eso es lo que diferencia a un sistema experto de una
> caja negra."

---

## PARTE 5 — Demostración de inferencias (5:30 – 7:30)

`[PANTALLA: Discord abierto con el bot TAI activo]`

> "Ahora voy a demostrar cómo funciona el motor de inferencias en vivo."

**[Ejecuta /crear_negocio]**
> "Primero creo mi cafetería. Le pongo el nombre y elijo la zona.
> Voy a elegir Col. Americana, que tiene un multiplicador de demanda
> de 1.3 y de renta de 1.4. Caja inicial: 100 mil pesos."

**[Ejecuta /ajustar_precio con precio = 80]**
> "Ahora voy a subir el precio a 80 pesos por taza, que está por encima
> del mercado de referencia que es 55 pesos. Voy a ver qué dice el sistema."

**[Ejecuta /ciclo_avanzar]**
> "Avanzo el primer ciclo. Vean el evento global que se generó.
> Ahora pulso **Ver explicación** para ver qué decidió el Agente Supervisor."

`[PANTALLA: Embed del Supervisor con las reglas disparadas]`

> "El sistema disparó la regla de **precio alto**: detectó que estoy
> cobrando por encima del mercado y me avisa que la demanda va a caer
> exponencialmente por la elasticidad-precio. Esa es la explicabilidad
> en acción: no solo me dice el resultado, me dice por qué."

**[Ejecuta /proveedor y compra grano de especialidad]**
> "Compro grano de especialidad. Esto va a activar la regla de reputación
> en el siguiente ciclo."

**[Ejecuta /ciclo_avanzar de nuevo]**
> "Avanzo otro ciclo y veo la explicación."

`[PANTALLA: Supervisor mostrando regla de grano especialidad]`

> "Aquí el sistema disparó la regla de **grano de especialidad**: reconoció
> que estoy usando grano de Chiapas o Veracruz y eleva la reputación del
> negocio un 15 por ciento, lo que compensa parcialmente el efecto del
> precio alto."

---

## PARTE 6 — Funcionamiento completo (7:30 – 9:00)

`[PANTALLA: Discord, recorre todos los comandos rápido]`

> "Para cerrar, un recorrido rápido de todas las funciones del sistema."

**[Muestra /dashboard]**
> "El dashboard muestra en tiempo real la caja, el precio por taza,
> el inventario desglosado por insumo, los resultados del último ciclo
> y tres indicadores clave: margen de contribución, punto de equilibrio
> en tazas por ciclo, y los costos fijos totales."

**[Muestra /marketing]**
> "El módulo de marketing permite lanzar campañas que elevan la demanda
> entre un 10 y un 25 por ciento. El efecto decae un 50 por ciento
> cada ciclo, modelando cómo el impacto publicitario se va diluyendo."

**[Muestra botón Vender]**
> "El botón Vender hace una venta rápida proporcional a la demanda
> actual sin avanzar el ciclo completo."

**[Muestra /borrar_negocio]**
> "Y si quiero empezar de cero, borrar negocio elimina todos los datos
> con confirmación."

---

## PARTE 7 — Cierre (9:00 – 9:45)

`[PANTALLA: Portada del PDF / diagrama de arquitectura]`

> "Para resumir: TAI es un sistema experto funcional que aplica los
> conceptos de la materia — base de conocimiento, motor de inferencias,
> agentes con roles definidos y explicabilidad — a un dominio real
> y concreto: la gestión económica de un negocio de café en Guadalajara."

> "El código está disponible en GitHub, el prototipo de interfaz en Figma,
> y el bot se puede agregar a cualquier servidor de Discord con el link
> de instalación que está en el README."

> "Gracias."

---

## Notas de producción

| Sección | Pantalla sugerida |
|---|---|
| Intro | Portada simple (Canva, PowerPoint o la portada del PDF) |
| Proyecto | Figma abierto en el navegador |
| Arquitectura | PDF abierto en la página del diagrama TikZ |
| Agentes | VS Code con `core/agentes.py` abierto |
| Inferencias | Discord en vivo con el bot corriendo |
| Funciones | Discord — recorre comandos rápido |
| Cierre | PDF o diagrama de arquitectura |

**Tip:** Graba el audio por separado con Audacity si hay ruido de fondo.  
Usa OBS con una fuente de captura de pantalla y el micrófono activado.

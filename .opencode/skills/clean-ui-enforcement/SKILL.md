---
name: clean-ui-enforcement
description: Garantiza que las interfaces de Gradio mantengan una estetica profesional y minimalista para OT.
license: MIT
compatibility: opencode
---

## Qué hago
Audito el código de la interfaz de usuario (Gradio) para asegurar que el diseño visual sea limpio, profesional y apto para entornos industriales (Inari Labs).

## Cuándo usarme
Usa esta habilidad siempre que estés escribiendo, modificando o refactorizando código dentro del directorio `ui/` o manipulando componentes de la interfaz gráfica.

## Reglas de ejecución
1. **Paleta de colores:** Utiliza colores sobrios (grises, blancos, azules corporativos). Evita colores neón, rojos agresivos o esquemas oscuros sobrecargados.
2. **Iconografía y UI:** Está estrictamente prohibido usar patrones de circuitos, código binario de fondo o iconografía técnica innecesaria. Prioriza la legibilidad del texto en planta.
3. **Validación:** Pregúntate: "¿Esta interfaz se lee claramente en la pantalla de una fábrica con mala iluminación?" Si la respuesta es no, simplifica el diseño.
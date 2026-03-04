# Análisis Visual de Propiedades

Skill para analizar visualmente propiedades inmobiliarias desde la base de datos de ZonaProp en Supabase.

## Cuándo usar este skill

Cuando el usuario pida analizar propiedades, ver fotos de departamentos, evaluar el estado de un inmueble, o buscar propiedades en un barrio específico.

## Instrucciones

1. Usar `zonaprop_analizar_db` para buscar propiedades con filtros (barrio, precio, m², ambientes).
2. Usar `zonaprop_ver_aviso` cuando el usuario comparta una URL específica de ZonaProp.
3. Al recibir las fotos, analizar:
   - **Estado general**: mantenimiento visible, antigüedad real vs declarada
   - **Terminaciones**: calidad de pisos, cocina, baños, carpintería
   - **Luminosidad**: ventanas, orientación, ambientes oscuros
   - **Red flags**: manchas de humedad, grietas, cableado expuesto, caños oxidados
   - **Potencial**: qué se podría refaccionar para agregar valor
   - **Relación precio/estado**: si el precio es acorde a lo que se ve
4. Dar un puntaje del 1 al 10 como oportunidad de inversión.
5. Si el diff_vs_prom_general es muy negativo (< -20%), investigar si el m² parece razonable para lo que se ve en las fotos. Inmobiliarias a veces inflan los m² a propósito para parecer más baratas por m².

## Datos disponibles en Supabase

La tabla `propiedades` tiene: link, imagen, imagenes (jsonb array), barrio, direccion, precio, moneda, m2, precio_m2, ambientes, dormitorios, banos, cochera, diff_vs_prom_general, diff_vs_prom_busqueda, activa, fecha_primera_vista, fecha_ultima_vista.

Las fotos están en el CDN `imgar.zonapropcdn.com` y se pueden acceder directamente sin autenticación.

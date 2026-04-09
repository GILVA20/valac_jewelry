import { z } from 'zod';
import { PRODUCT_TYPES, GENDERS, MATERIALS } from './constants';

export const productSchema = z.object({
  nombre: z.string().trim().min(1, 'El nombre es obligatorio').max(200),
  descripcion: z.string().max(2000).default('Sin descripción'),
  precio: z.coerce.number().min(100, 'Precio mínimo: $100 MXN'),
  descuento_pct: z.coerce.number().min(0).max(100).default(0),
  tipo_producto: z.string().refine(v => (PRODUCT_TYPES as readonly string[]).includes(v), 'Tipo inválido'),
  genero: z.string().refine(v => (GENDERS as readonly string[]).includes(v), 'Género inválido'),
  tipo_oro: z.string().refine(v => (MATERIALS as readonly string[]).includes(v), 'Material inválido'),
  imagen: z.string().nullable().optional(),
  stock_total: z.coerce.number().min(0).default(0),
  activo: z.boolean().default(false),
  destacado: z.boolean().default(false),
});

export type ProductSchemaType = z.infer<typeof productSchema>;

export const csvRowSchema = z.object({
  nombre: z.string().min(1),
  descripcion: z.string().optional().default('Sin descripción'),
  precio: z.coerce.number().min(100),
  tipo_producto: z.string().refine(v => (PRODUCT_TYPES as readonly string[]).includes(v)),
  genero: z.string().transform(v => {
    const capitalized = v.charAt(0).toUpperCase() + v.slice(1).toLowerCase();
    return capitalized;
  }).refine(v => (GENDERS as readonly string[]).includes(v)),
  tipo_oro: z.string().refine(v => (MATERIALS as readonly string[]).includes(v)),
  imagen: z.string().optional().default(''),
  stock_total: z.coerce.number().min(0).default(0).catch(0),
});

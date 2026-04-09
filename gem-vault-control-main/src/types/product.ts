export interface Product {
  id: number;
  nombre: string;
  descripcion: string;
  precio: number;
  descuento_pct: number;
  precio_descuento: number;
  tipo_producto: string;
  genero: string;
  tipo_oro: string;
  imagen: string | null;
  stock_total: number;
  activo: boolean;
  destacado: boolean;
  external_id: string | null;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  updated_by: string | null;
  product_images?: ProductImage[];
}

export interface ProductImage {
  id: number;
  product_id: number;
  imagen: string;
  orden: number;
}

export type ProductInsert = Omit<Product, 'id' | 'created_at' | 'updated_at' | 'product_images'>;
export type ProductUpdate = Partial<ProductInsert>;

export interface ProductFormData {
  nombre: string;
  descripcion: string;
  precio: number;
  descuento_pct: number;
  tipo_producto: string;
  genero: string;
  tipo_oro: string;
  imagen: string | null;
  stock_total: number;
  activo: boolean;
  destacado: boolean;
}

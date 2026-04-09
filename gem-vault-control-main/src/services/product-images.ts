import { supabase } from './supabase';
import type { ProductImage } from '@/types/product';
import { STORAGE_BUCKET } from '@/lib/constants';

export async function uploadProductImage(file: File): Promise<string> {
  const timestamp = Date.now();
  const ext = file.name.split('.').pop() || 'webp';
  const path = `products/${timestamp}-${crypto.randomUUID()}.${ext}`;

  const { error } = await supabase.storage
    .from(STORAGE_BUCKET)
    .upload(path, file, { contentType: file.type });
  if (error) throw error;

  const { data } = supabase.storage.from(STORAGE_BUCKET).getPublicUrl(path);
  return data.publicUrl;
}

export async function addProductImage(productId: number, imageUrl: string, orden: number): Promise<ProductImage> {
  const { data, error } = await supabase
    .from('product_images')
    .insert({ product_id: productId, imagen: imageUrl, orden })
    .select()
    .single();
  if (error) throw error;
  return data as ProductImage;
}

export async function deleteProductImage(imageId: number): Promise<void> {
  const { error } = await supabase.from('product_images').delete().eq('id', imageId);
  if (error) throw error;
}

export async function reorderImages(images: { id: number; orden: number }[]): Promise<void> {
  for (const img of images) {
    await supabase.from('product_images').update({ orden: img.orden }).eq('id', img.id);
  }
}

export async function setPrimaryImage(productId: number, imageUrl: string): Promise<void> {
  const { error } = await supabase
    .from('products')
    .update({ imagen: imageUrl })
    .eq('id', productId);
  if (error) throw error;
}

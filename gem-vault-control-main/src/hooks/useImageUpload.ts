import { useState } from 'react';
import { uploadProductImage } from '@/services/product-images';
import { toast } from 'sonner';

export function useImageUpload() {
  const [uploading, setUploading] = useState(false);

  const upload = async (file: File): Promise<string | null> => {
    setUploading(true);
    try {
      const url = await uploadProductImage(file);
      return url;
    } catch (e: unknown) {
      toast.error('Error al subir imagen: ' + (e instanceof Error ? e.message : 'Unknown'));
      return null;
    } finally {
      setUploading(false);
    }
  };

  return { upload, uploading };
}

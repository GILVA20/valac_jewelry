import { useCallback, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { productSchema, type ProductSchemaType } from '@/lib/validators';
import { useProduct } from '@/hooks/useProduct';
import { useProductMutations } from '@/hooks/useProductMutations';
import { useImageUpload } from '@/hooks/useImageUpload';
import { PRODUCT_TYPES, GENDERS, MATERIALS } from '@/lib/constants';
import { AppLayout } from '@/components/layout/AppLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import { Skeleton } from '@/components/ui/skeleton';
import { ArrowLeft, Upload, ImageIcon, Star } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ProductInsert } from '@/types/product';

export default function ProductFormPage() {
  const navigate = useNavigate();
  const { id } = useParams();
  const isEdit = !!id;
  const productId = id ? Number(id) : undefined;
  const { data: product, isLoading } = useProduct(productId);
  const { create, update } = useProductMutations();
  const { upload, uploading } = useImageUpload();
  const [previewImage, setPreviewImage] = useState<string | null>(null);

  const form = useForm<ProductSchemaType>({
    resolver: zodResolver(productSchema),
    values: product ? {
      nombre: product.nombre,
      descripcion: product.descripcion,
      precio: product.precio,
      descuento_pct: product.descuento_pct,
      tipo_producto: product.tipo_producto,
      genero: product.genero,
      tipo_oro: product.tipo_oro,
      imagen: product.imagen,
      stock_total: product.stock_total,
      activo: product.activo,
      destacado: product.destacado,
    } : undefined,
  });

  const precio = form.watch('precio') || 0;
  const descuento = form.watch('descuento_pct') || 0;
  const precioFinal = precio * (1 - descuento / 100);
  const currentImage = previewImage || form.watch('imagen');

  const onSubmit = useCallback(async (data: ProductSchemaType) => {
    const payload = {
      nombre: data.nombre,
      descripcion: data.descripcion || 'Sin descripción',
      precio: data.precio,
      descuento_pct: data.descuento_pct || 0,
      imagen: data.imagen || null,
      precio_descuento: data.precio * (1 - (data.descuento_pct || 0) / 100),
      tipo_producto: data.tipo_producto,
      genero: data.genero,
      tipo_oro: data.tipo_oro,
      stock_total: data.stock_total || 0,
      activo: data.activo || false,
      destacado: data.destacado || false,
      external_id: null as string | null,
      created_by: null as string | null,
      updated_by: null as string | null,
    };

    if (isEdit && productId) {
      await update.mutateAsync({ id: productId, data: payload });
    } else {
      await create.mutateAsync(payload);
    }
    navigate('/');
  }, [isEdit, productId, update, create, navigate]);

  const handleImageUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPreviewImage(URL.createObjectURL(file));
    const url = await upload(file);
    if (url) {
      form.setValue('imagen', url);
      setPreviewImage(url);
    }
  }, [upload, form]);

  if (isEdit && isLoading) {
    return (
      <AppLayout>
        <div className="p-6 max-w-5xl mx-auto space-y-6">
          <Skeleton className="h-8 w-48" />
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-6">
            <div className="space-y-4">
              {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20 w-full" />)}
            </div>
            <Skeleton className="h-[400px]" />
          </div>
        </div>
      </AppLayout>
    );
  }

  const fmt = (n: number) => new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(n);

  return (
    <AppLayout>
      <form onSubmit={form.handleSubmit(onSubmit)} className="p-6 max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <Button type="button" variant="ghost" size="icon" onClick={() => navigate('/')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <h1 className="text-xl font-semibold">{isEdit ? 'Editar producto' : 'Nuevo producto'}</h1>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-6">
          {/* Left column */}
          <div className="space-y-6">
            {/* Basic info */}
            <div className="bg-card border border-border rounded-lg p-5 space-y-4">
              <h2 className="text-sm font-semibold">Información básica</h2>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Nombre *</label>
                <Input {...form.register('nombre')} placeholder="Anillo Solitario Oro 14k" />
                {form.formState.errors.nombre && <p className="text-xs text-destructive mt-1">{form.formState.errors.nombre.message}</p>}
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Descripción</label>
                <Textarea {...form.register('descripcion')} rows={3} placeholder="Descripción del producto..." />
                <p className="text-[10px] text-muted-foreground text-right mt-1">{(form.watch('descripcion') || '').length}/2000</p>
              </div>
            </div>

            {/* Pricing */}
            <div className="bg-card border border-border rounded-lg p-5 space-y-4">
              <h2 className="text-sm font-semibold">Precio y descuento</h2>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Precio (MXN) *</label>
                  <Input type="number" step="0.01" {...form.register('precio')} placeholder="0.00" />
                  {form.formState.errors.precio && <p className="text-xs text-destructive mt-1">{form.formState.errors.precio.message}</p>}
                </div>
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Descuento: {descuento}%</label>
                  <Controller
                    name="descuento_pct"
                    control={form.control}
                    render={({ field }) => (
                      <Slider
                        min={0}
                        max={100}
                        step={1}
                        value={[field.value || 0]}
                        onValueChange={([v]) => field.onChange(v)}
                        className="mt-3"
                      />
                    )}
                  />
                </div>
              </div>
              {descuento > 0 && (
                <div className="flex items-center gap-2 text-sm bg-accent p-3 rounded-md">
                  <span className="text-muted-foreground line-through">{fmt(precio)}</span>
                  <span className="font-semibold text-accent-foreground">{fmt(precioFinal)}</span>
                  <span className="text-xs text-destructive ml-auto">-{descuento}%</span>
                </div>
              )}
            </div>

            {/* Organization */}
            <div className="bg-card border border-border rounded-lg p-5 space-y-4">
              <h2 className="text-sm font-semibold">Organización</h2>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Tipo *</label>
                  <Controller
                    name="tipo_producto"
                    control={form.control}
                    render={({ field }) => (
                      <Select value={field.value} onValueChange={field.onChange}>
                        <SelectTrigger><SelectValue placeholder="Seleccionar" /></SelectTrigger>
                        <SelectContent>
                          {PRODUCT_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    )}
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Material *</label>
                  <Controller
                    name="tipo_oro"
                    control={form.control}
                    render={({ field }) => (
                      <Select value={field.value} onValueChange={field.onChange}>
                        <SelectTrigger><SelectValue placeholder="Seleccionar" /></SelectTrigger>
                        <SelectContent>
                          {MATERIALS.map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    )}
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Género *</label>
                  <Controller
                    name="genero"
                    control={form.control}
                    render={({ field }) => (
                      <div className="flex gap-1">
                        {GENDERS.map((g) => (
                          <button
                            key={g}
                            type="button"
                            onClick={() => field.onChange(g)}
                            className={cn(
                              'px-3 py-1.5 text-xs rounded-md border transition-colors flex-1',
                              field.value === g ? 'border-primary bg-primary text-primary-foreground' : 'border-border text-muted-foreground hover:bg-muted'
                            )}
                          >
                            {g}
                          </button>
                        ))}
                      </div>
                    )}
                  />
                </div>
              </div>
            </div>

            {/* Inventory */}
            <div className="bg-card border border-border rounded-lg p-5 space-y-4">
              <h2 className="text-sm font-semibold">Inventario</h2>
              <div className="max-w-[200px]">
                <label className="text-xs text-muted-foreground mb-1 block">Stock total</label>
                <Input type="number" min={0} {...form.register('stock_total')} />
              </div>
            </div>
          </div>

          {/* Right column */}
          <div className="space-y-6">
            {/* Status */}
            <div className="bg-card border border-border rounded-lg p-5 space-y-3">
              <h2 className="text-sm font-semibold">Estado</h2>
              <Controller
                name="activo"
                control={form.control}
                render={({ field }) => (
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium">{field.value ? 'Activo' : 'Borrador'}</p>
                      <p className="text-xs text-muted-foreground">
                        {field.value ? 'Visible en la tienda' : 'No visible para clientes'}
                      </p>
                    </div>
                    <Switch checked={field.value} onCheckedChange={field.onChange} />
                  </div>
                )}
              />
            </div>

            {/* Image */}
            <div className="bg-card border border-border rounded-lg p-5 space-y-3">
              <h2 className="text-sm font-semibold">Imagen principal</h2>
              {currentImage ? (
                <div className="relative">
                  <img src={currentImage} alt="Preview" className="w-full aspect-square object-cover rounded-md" />
                  <label className="absolute bottom-2 right-2">
                    <input type="file" accept="image/*" className="hidden" onChange={handleImageUpload} />
                    <Button type="button" variant="secondary" size="sm" asChild>
                      <span>{uploading ? 'Subiendo...' : 'Cambiar'}</span>
                    </Button>
                  </label>
                </div>
              ) : (
                <label
                  className="border-2 border-dashed border-border rounded-lg p-8 text-center hover:border-primary/50 transition-colors cursor-pointer block"
                >
                  <input type="file" accept="image/*" className="hidden" onChange={handleImageUpload} />
                  {uploading ? (
                    <p className="text-sm text-muted-foreground">Subiendo...</p>
                  ) : (
                    <>
                      <Upload className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                      <p className="text-xs text-muted-foreground">Arrastra o haz clic</p>
                      <p className="text-[10px] text-muted-foreground mt-1">JPG, PNG, WEBP</p>
                    </>
                  )}
                </label>
              )}
            </div>

            {/* Featured */}
            <div className="bg-card border border-border rounded-lg p-5">
              <Controller
                name="destacado"
                control={form.control}
                render={({ field }) => (
                  <label className="flex items-center gap-3 cursor-pointer">
                    <div className={cn('w-8 h-8 rounded-md flex items-center justify-center', field.value ? 'bg-primary' : 'bg-muted')}>
                      <Star className={cn('h-4 w-4', field.value ? 'text-primary-foreground' : 'text-muted-foreground')} />
                    </div>
                    <div>
                      <p className="text-sm font-medium">Destacado</p>
                      <p className="text-xs text-muted-foreground">Mostrar en homepage</p>
                    </div>
                    <Switch checked={field.value} onCheckedChange={field.onChange} className="ml-auto" />
                  </label>
                )}
              />
            </div>

            {/* Meta info */}
            {isEdit && product && (
              <div className="bg-card border border-border rounded-lg p-5 space-y-2">
                <h2 className="text-sm font-semibold">Información</h2>
                <div className="text-xs text-muted-foreground space-y-1">
                  <p>Creado: {new Date(product.created_at).toLocaleDateString('es-MX')}</p>
                  <p>Actualizado: {new Date(product.updated_at).toLocaleDateString('es-MX')}</p>
                  {product.external_id && <p>ID externo: {product.external_id}</p>}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-background border-t border-border mt-6 -mx-6 px-6 py-4 flex items-center justify-end gap-3">
          <Button type="button" variant="outline" onClick={() => navigate('/')}>Cancelar</Button>
          <Button type="submit" disabled={create.isPending || update.isPending}>
            {(create.isPending || update.isPending) ? 'Guardando...' : 'Guardar'}
          </Button>
        </div>
      </form>
    </AppLayout>
  );
}

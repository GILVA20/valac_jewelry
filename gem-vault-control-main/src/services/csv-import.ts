import Papa from 'papaparse';
import { csvRowSchema } from '@/lib/validators';
import { supabase } from './supabase';

export interface CsvRow {
  rowIndex: number;
  raw: Record<string, string>;
  parsed: Record<string, unknown> | null;
  errors: string[];
  warnings: string[];
  valid: boolean;
}

export interface CsvParseResult {
  rows: CsvRow[];
  columns: string[];
  validCount: number;
  errorCount: number;
  warningCount: number;
}

export function parseCsvFile(file: File): Promise<CsvParseResult> {
  return new Promise((resolve, reject) => {
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        const columns = results.meta.fields || [];
        const rows: CsvRow[] = results.data.map((raw: unknown, i: number) => {
          const record = raw as Record<string, string>;
          const result = csvRowSchema.safeParse(record);
          const warnings: string[] = [];

          if (record.stock_total && Number(record.stock_total) < 0) {
            warnings.push('Stock negativo ajustado a 0');
          }

          if (result.success) {
            return { rowIndex: i, raw: record, parsed: result.data, errors: [], warnings, valid: true };
          }
          const errors = result.error.issues.map(e => `${e.path.join('.')}: ${e.message}`);
          return { rowIndex: i, raw: record, parsed: null, errors, warnings, valid: false };
        });

        resolve({
          rows,
          columns,
          validCount: rows.filter(r => r.valid).length,
          errorCount: rows.filter(r => !r.valid).length,
          warningCount: rows.filter(r => r.warnings.length > 0).length,
        });
      },
      error: reject,
    });
  });
}

export async function importCsvRows(
  rows: CsvRow[],
  onProgress?: (current: number, total: number) => void
): Promise<number[]> {
  const validRows = rows.filter(r => r.valid && r.parsed);
  const insertedIds: number[] = [];

  for (let i = 0; i < validRows.length; i++) {
    const row = validRows[i].parsed!;
    const precio = Number(row.precio);
    const descuento_pct = 0;

    const { data, error } = await supabase
      .from('products')
      .insert({
        nombre: row.nombre as string,
        descripcion: (row.descripcion as string) || 'Sin descripción',
        precio,
        descuento_pct,
        precio_descuento: precio,
        tipo_producto: row.tipo_producto as string,
        genero: row.genero as string,
        tipo_oro: row.tipo_oro as string,
        imagen: (row.imagen as string) || null,
        stock_total: Number(row.stock_total) || 0,
        activo: false,
      })
      .select('id')
      .single();

    if (!error && data) insertedIds.push(data.id);
    onProgress?.(i + 1, validRows.length);
  }

  return insertedIds;
}

import type { StageResult, Product } from "./studio-types";

const BASE = "/admin/studio";

async function pollJob<T>(jobId: string): Promise<T> {
  while (true) {
    await new Promise((r) => setTimeout(r, 3000));
    const res = await fetch(`${BASE}/job/${jobId}`);
    if (!res.ok) throw new Error("Error polling job");
    const data = await res.json();
    if (data.status === "processing") continue;
    if (data.status === "error") throw new Error(data.error || "Job failed");
    return data as T;
  }
}

export async function generateStage1(data: {
  images: string[];
  sexo: string;
  categoria: string;
  modo: string;
  feedback?: string[];
}): Promise<{ results: StageResult[] }> {
  const res = await fetch(`${BASE}/generate/stage1`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Error en Stage 1");
  const { job_id } = await res.json();
  return pollJob<{ results: StageResult[] }>(job_id);
}

export async function generateStage2(data: {
  product_images: string[];
  product_studio_images: string[];
  base_image: string;
  sexo: string;
  categoria: string;
  descriptions: string[];
  feedback?: string[];
}): Promise<{ results: StageResult[] }> {
  const res = await fetch(`${BASE}/generate/stage2`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Error en Stage 2");
  const { job_id } = await res.json();
  return pollJob<{ results: StageResult[] }>(job_id);
}

export async function saveToProduct(data: {
  image_base64: string;
  producto_id: string;
}): Promise<{ success: boolean; image_url: string }> {
  const res = await fetch(`${BASE}/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Error al guardar");
  return res.json();
}

export async function fetchProducts(): Promise<Product[]> {
  const res = await fetch(`${BASE}/products`);
  if (!res.ok) throw new Error("Error cargando productos");
  const data = await res.json();
  return data.products;
}

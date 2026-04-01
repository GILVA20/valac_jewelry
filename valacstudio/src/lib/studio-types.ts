export type Sexo = "hombre" | "mujer";
export type Modo = "individual" | "bulk";

export const CATEGORIAS: Record<Sexo, string[]> = {
  hombre: ["Collar + Dije", "Cadena", "Pulso", "Anillo", "Arete"],
  mujer: ["Arete", "Cadena", "Pulso", "Anillo", "Dije"],
};

export interface StageResult {
  image_base64: string;
  product_image_base64?: string;
  status: "approved" | "review";
  reason?: string;
  description?: string;
}

export interface StudioState {
  step: number;
  sexo: Sexo;
  categoria: string;
  modo: Modo;
  rawImages: string[]; // base64
  stage1Results: StageResult[];
  selectedResults: number[]; // indices of accepted stage1 results
  selectedBase: string;
  stage2Results: StageResult[];
  selectedFinals: number[];
}

export const initialStudioState: StudioState = {
  step: 1,
  sexo: "mujer",
  categoria: "",
  modo: "individual",
  rawImages: [],
  stage1Results: [],
  selectedResults: [],
  selectedBase: "",
  stage2Results: [],
  selectedFinals: [],
};

export interface Product {
  id: string;
  nombre: string;
}

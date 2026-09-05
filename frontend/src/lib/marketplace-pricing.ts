import { apiFetch } from './api';

export type MarketplaceId = 'mercado_livre' | 'shopee';

export interface MarketplaceFees {
  commissionPercent: number;
  paymentFeePercent: number;
  taxPercent: number;
  advertisingPercent: number;
  fixedFee: number;
  shippingCost: number;
}

export interface ManualProduct {
  id: string;
  sku: string;
  name: string;
  productCost: number;
  packagingCost: number;
  operationalCost: number;
  desiredMarginPercent: number;
  promotionalMarginPercent: number;
  currentPrice: number;
}

export type PricingAlert =
  | 'sem_preco'
  | 'abaixo_minimo'
  | 'margem_critica'
  | 'abaixo_recomendado'
  | 'saudavel';

export interface PricingResult {
  marketplace: MarketplaceId;
  minimumPrice: number;
  recommendedPrice: number;
  promotionalPrice: number;
  currentProfit: number | null;
  currentMarginPercent: number | null;
  alert: PricingAlert;
}

export interface PricingComparison {
  mercado_livre: PricingResult;
  shopee: PricingResult;
  lowestRecommendedMarketplace: MarketplaceId;
  recommendedDifference: number;
}

export const emptyFees = (): MarketplaceFees => ({
  commissionPercent: 0,
  paymentFeePercent: 0,
  taxPercent: 0,
  advertisingPercent: 0,
  fixedFee: 0,
  shippingCost: 0,
});

export const createProduct = (sequence = Date.now()): ManualProduct => ({
  id: `${sequence}-${Math.random().toString(36).slice(2, 8)}`,
  sku: `SKU-${String(sequence).slice(-4)}`,
  name: 'Novo produto',
  productCost: 0,
  packagingCost: 0,
  operationalCost: 0,
  desiredMarginPercent: 20,
  promotionalMarginPercent: 10,
  currentPrice: 0,
});

const requireFiniteNonNegative = (value: number, label: string) => {
  if (!Number.isFinite(value) || value < 0) {
    throw new Error(`${label} não pode ser negativo.`);
  }
};

const ceilMoney = (value: number) => Math.ceil((value - Number.EPSILON) * 100) / 100;
const roundMoney = (value: number) => Math.round((value + Number.EPSILON) * 100) / 100;

export function calculatePricing(
  product: ManualProduct,
  marketplace: MarketplaceId,
  fees: MarketplaceFees,
): PricingResult {
  if (!product.sku.trim()) throw new Error('Informe o SKU do produto.');
  if (!product.name.trim()) throw new Error('Informe o nome do produto.');
  [
    [product.productCost, 'Custo do produto'],
    [product.packagingCost, 'Embalagem'],
    [product.operationalCost, 'Outros custos'],
    [product.desiredMarginPercent, 'Margem desejada'],
    [product.promotionalMarginPercent, 'Margem promocional'],
    [product.currentPrice, 'Preço atual'],
    [fees.commissionPercent, 'Comissão'],
    [fees.paymentFeePercent, 'Tarifa de pagamento'],
    [fees.taxPercent, 'Impostos'],
    [fees.advertisingPercent, 'Publicidade'],
    [fees.fixedFee, 'Tarifa fixa'],
    [fees.shippingCost, 'Frete'],
  ].forEach(([value, label]) => requireFiniteNonNegative(value as number, label as string));
  if (product.productCost <= 0) throw new Error('O custo do produto precisa ser maior que zero.');
  if (product.promotionalMarginPercent > product.desiredMarginPercent) {
    throw new Error('A margem promocional não pode superar a margem desejada.');
  }

  const variablePercent = fees.commissionPercent + fees.paymentFeePercent
    + fees.taxPercent + fees.advertisingPercent;
  const fixedCost = product.productCost + product.packagingCost + product.operationalCost
    + fees.fixedFee + fees.shippingCost;
  const target = (margin: number) => {
    const denominator = 1 - variablePercent / 100 - margin / 100;
    if (denominator <= 0) throw new Error('Taxas e margem deixam o preço inviável.');
    return ceilMoney(fixedCost / denominator);
  };
  const minimumPrice = target(0);
  const promotionalPrice = target(product.promotionalMarginPercent);
  const recommendedPrice = target(product.desiredMarginPercent);
  let currentProfit: number | null = null;
  let currentMarginPercent: number | null = null;
  let alert: PricingAlert = 'sem_preco';
  if (product.currentPrice > 0) {
    currentProfit = roundMoney(product.currentPrice * (1 - variablePercent / 100) - fixedCost);
    currentMarginPercent = roundMoney(currentProfit / product.currentPrice * 100);
    if (product.currentPrice < minimumPrice) alert = 'abaixo_minimo';
    else if (currentMarginPercent < product.promotionalMarginPercent) alert = 'margem_critica';
    else if (currentMarginPercent < product.desiredMarginPercent) alert = 'abaixo_recomendado';
    else alert = 'saudavel';
  }
  return {
    marketplace,
    minimumPrice,
    recommendedPrice,
    promotionalPrice,
    currentProfit,
    currentMarginPercent,
    alert,
  };
}

export function compareMarketplaces(
  product: ManualProduct,
  fees: Record<MarketplaceId, MarketplaceFees>,
): PricingComparison {
  const mercadoLivre = calculatePricing(product, 'mercado_livre', fees.mercado_livre);
  const shopee = calculatePricing(product, 'shopee', fees.shopee);
  const lowest = mercadoLivre.recommendedPrice <= shopee.recommendedPrice
    ? 'mercado_livre' : 'shopee';
  return {
    mercado_livre: mercadoLivre,
    shopee,
    lowestRecommendedMarketplace: lowest,
    recommendedDifference: roundMoney(Math.abs(mercadoLivre.recommendedPrice - shopee.recommendedPrice)),
  };
}

function parseDelimited(text: string): string[][] {
  const firstLine = text.split(/\r?\n/, 1)[0] ?? '';
  const delimiter = (firstLine.match(/;/g)?.length ?? 0) > (firstLine.match(/,/g)?.length ?? 0) ? ';' : ',';
  const rows: string[][] = [];
  let row: string[] = [];
  let field = '';
  let quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (char === '"') {
      if (quoted && text[index + 1] === '"') { field += '"'; index += 1; }
      else quoted = !quoted;
    } else if (char === delimiter && !quoted) {
      row.push(field); field = '';
    } else if ((char === '\n' || char === '\r') && !quoted) {
      if (char === '\r' && text[index + 1] === '\n') index += 1;
      row.push(field); field = '';
      if (row.some((cell) => cell.trim())) rows.push(row);
      row = [];
    } else field += char;
  }
  row.push(field);
  if (row.some((cell) => cell.trim())) rows.push(row);
  return rows;
}

const normalizeHeader = (value: unknown) => String(value ?? '').trim().toLowerCase()
  .normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');

const aliases: Record<string, string[]> = {
  sku: ['sku', 'codigo', 'codigo_sku'],
  name: ['nome', 'produto', 'name', 'titulo'],
  productCost: ['custo', 'custo_produto', 'product_cost', 'productcost'],
  packagingCost: ['embalagem', 'custo_embalagem', 'packaging_cost', 'packagingcost'],
  operationalCost: ['outros_custos', 'custo_operacional', 'operational_cost', 'operationalcost'],
  desiredMarginPercent: ['margem_desejada', 'margem', 'desired_margin_percent', 'desiredmarginpercent'],
  promotionalMarginPercent: ['margem_promocional', 'promotional_margin_percent', 'promotionalmarginpercent'],
  currentPrice: ['preco_atual', 'preco', 'sale_price', 'current_price', 'currentprice'],
};

function localizedNumber(value: unknown, fallback = 0): number {
  if (typeof value === 'number') return Number.isFinite(value) ? value : fallback;
  const raw = String(value ?? '').trim().replace(/R\$|%|\s/g, '');
  if (!raw) return fallback;
  const normalized = raw.includes(',') ? raw.replace(/\./g, '').replace(',', '.') : raw;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export function mapImportedRows(rows: Array<Record<string, unknown>>): ManualProduct[] {
  return rows.slice(0, 1000).map((source, index) => {
    const normalized = Object.fromEntries(Object.entries(source).map(([key, value]) => [normalizeHeader(key), value]));
    const valueFor = (field: keyof typeof aliases) => {
      const key = aliases[field].find((candidate) => candidate in normalized);
      return key ? normalized[key] : undefined;
    };
    const sku = String(valueFor('sku') ?? '').trim();
    const name = String(valueFor('name') ?? '').trim();
    if (!sku || !name) throw new Error(`Linha ${index + 2}: informe SKU e nome.`);
    return {
      id: `import-${Date.now()}-${index}`,
      sku,
      name,
      productCost: localizedNumber(valueFor('productCost')),
      packagingCost: localizedNumber(valueFor('packagingCost')),
      operationalCost: localizedNumber(valueFor('operationalCost')),
      desiredMarginPercent: localizedNumber(valueFor('desiredMarginPercent'), 20),
      promotionalMarginPercent: localizedNumber(valueFor('promotionalMarginPercent'), 10),
      currentPrice: localizedNumber(valueFor('currentPrice')),
    };
  });
}

export function parseCsv(text: string): ManualProduct[] {
  const rows = parseDelimited(text.replace(/^\uFEFF/, ''));
  if (rows.length < 2) throw new Error('O CSV precisa ter cabeçalho e ao menos um produto.');
  const headers = rows[0];
  return mapImportedRows(rows.slice(1).map((row) => Object.fromEntries(headers.map((header, index) => [header, row[index] ?? '']))));
}

export async function parseProductFile(file: File): Promise<ManualProduct[]> {
  const extension = file.name.split('.').pop()?.toLowerCase();
  if (extension === 'csv') return parseCsv(await file.text());
  if (extension === 'xlsx') {
    const body = new FormData();
    body.append('file', file);
    const response = await apiFetch('/v1/pricing/import', { method: 'POST', body });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || payload.error || `Falha ao importar Excel (${response.status}).`);
    }
    if (!Array.isArray(payload.products)) {
      throw new Error('O importador retornou uma resposta inválida.');
    }
    return mapImportedRows(payload.products);
  }
  throw new Error('Formato não suportado. Use CSV ou XLSX.');
}

import { useEffect, useMemo, useRef, useState } from 'react';
import { AlertTriangle, Calculator, FileSpreadsheet, Plus, Save, Trash2, Upload } from 'lucide-react';
import { toast } from 'sonner';
import {
  compareMarketplaces,
  createProduct,
  emptyFees,
  parseProductFile,
  type ManualProduct,
  type MarketplaceFees,
  type MarketplaceId,
  type PricingAlert,
} from '../lib/marketplace-pricing';

const STORAGE_KEY = 'zeusex-marketplace-pricing-v1';
const marketplaceLabels: Record<MarketplaceId, string> = {
  mercado_livre: 'Mercado Livre', shopee: 'Shopee',
};
const alertLabels: Record<PricingAlert, string> = {
  sem_preco: 'Informe o preço atual',
  abaixo_minimo: 'Preço abaixo do mínimo',
  margem_critica: 'Margem crítica',
  abaixo_recomendado: 'Abaixo da margem desejada',
  saudavel: 'Preço saudável',
};
const alertColors: Record<PricingAlert, string> = {
  sem_preco: 'var(--color-text-tertiary)', abaixo_minimo: 'var(--color-error)',
  margem_critica: 'var(--color-warning)', abaixo_recomendado: 'var(--color-warning)',
  saudavel: 'var(--color-success)',
};
const money = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

interface StoredState {
  products: ManualProduct[];
  fees: Record<MarketplaceId, MarketplaceFees>;
}

const initialState = (): StoredState => {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null') as StoredState | null;
    if (parsed?.products?.length && parsed.fees?.mercado_livre && parsed.fees?.shopee) return parsed;
  } catch { /* start clean if local storage is invalid */ }
  return { products: [createProduct()], fees: { mercado_livre: emptyFees(), shopee: emptyFees() } };
};

function NumberField({ label, value, onChange, suffix }: { label: string; value: number; onChange: (value: number) => void; suffix?: string }) {
  return (
    <label className="grid gap-1.5 text-xs text-[var(--color-text-secondary)]">
      {label}
      <span className="flex items-center rounded-lg border border-[var(--color-input-border)] bg-[var(--color-input-bg)] focus-within:border-[var(--color-accent)]">
        <input type="number" min="0" step="0.01" value={Number.isFinite(value) ? value : 0}
          onChange={(event) => onChange(Number(event.target.value))}
          className="min-w-0 flex-1 bg-transparent px-3 py-2 text-sm text-[var(--color-text)] outline-none" />
        {suffix && <span className="pr-3 text-[var(--color-text-tertiary)]">{suffix}</span>}
      </span>
    </label>
  );
}

function MarketplaceSettings({ marketplace, value, onChange }: { marketplace: MarketplaceId; value: MarketplaceFees; onChange: (value: MarketplaceFees) => void }) {
  const set = (key: keyof MarketplaceFees, next: number) => onChange({ ...value, [key]: next });
  return (
    <article className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-4">
      <h3 className="mb-4 font-medium">{marketplaceLabels[marketplace]}</h3>
      <div className="grid gap-3 sm:grid-cols-2">
        <NumberField label="Comissão" value={value.commissionPercent} onChange={(v) => set('commissionPercent', v)} suffix="%" />
        <NumberField label="Tarifa de pagamento" value={value.paymentFeePercent} onChange={(v) => set('paymentFeePercent', v)} suffix="%" />
        <NumberField label="Impostos" value={value.taxPercent} onChange={(v) => set('taxPercent', v)} suffix="%" />
        <NumberField label="Publicidade" value={value.advertisingPercent} onChange={(v) => set('advertisingPercent', v)} suffix="%" />
        <NumberField label="Tarifa fixa" value={value.fixedFee} onChange={(v) => set('fixedFee', v)} suffix="R$" />
        <NumberField label="Frete pago por você" value={value.shippingCost} onChange={(v) => set('shippingCost', v)} suffix="R$" />
      </div>
    </article>
  );
}

export function PricingPage() {
  const [state, setState] = useState<StoredState>(initialState);
  const [selectedId, setSelectedId] = useState(state.products[0]?.id ?? '');
  const fileRef = useRef<HTMLInputElement>(null);
  const selected = state.products.find((product) => product.id === selectedId) ?? state.products[0];

  useEffect(() => { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }, [state]);
  useEffect(() => {
    if (!state.products.some((product) => product.id === selectedId)) setSelectedId(state.products[0]?.id ?? '');
  }, [state.products, selectedId]);

  const calculation = useMemo(() => {
    if (!selected) return { comparison: null, error: '' };
    try {
      return { comparison: compareMarketplaces(selected, state.fees), error: '' };
    } catch (reason) {
      return { comparison: null, error: reason instanceof Error ? reason.message : 'Não foi possível calcular.' };
    }
  }, [selected, state.fees]);
  const { comparison, error } = calculation;

  const updateProduct = (patch: Partial<ManualProduct>) => setState((current) => ({
    ...current,
    products: current.products.map((product) => product.id === selected.id ? { ...product, ...patch } : product),
  }));
  const addProduct = () => {
    const product = createProduct();
    setState((current) => ({ ...current, products: [...current.products, product] }));
    setSelectedId(product.id);
  };
  const deleteProduct = () => {
    if (state.products.length === 1) return;
    setState((current) => ({ ...current, products: current.products.filter((product) => product.id !== selected.id) }));
  };
  const importFile = async (file: File) => {
    try {
      const imported = await parseProductFile(file);
      if (!imported.length) throw new Error('Nenhum produto encontrado no arquivo.');
      setState((current) => ({ ...current, products: [...current.products, ...imported].slice(0, 1000) }));
      setSelectedId(imported[0].id);
      toast.success(`${imported.length} produto(s) importado(s).`);
    } catch (reason) { toast.error(reason instanceof Error ? reason.message : 'Falha ao importar arquivo.'); }
    if (fileRef.current) fileRef.current.value = '';
  };

  if (!selected) return null;
  const invalidSkuCount = state.products.filter((product) => !product.sku.trim()).length;
  let belowMinimumCount = 0;
  for (const product of state.products) {
    try {
      const result = compareMarketplaces(product, state.fees);
      if (result.mercado_livre.alert === 'abaixo_minimo' || result.shopee.alert === 'abaixo_minimo') belowMinimumCount += 1;
    } catch { /* surfaced in the editor */ }
  }

  return (
    <div className="relative h-full overflow-y-auto">
      <div className="hud-backdrop" />
      <main className="relative z-10 mx-auto flex w-full max-w-7xl flex-col gap-5 p-5 md:p-8">
        <section className="hud-panel p-6 md:p-8">
          <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
            <div>
              <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-accent-subtle)] px-3 py-1.5 text-xs text-[var(--color-accent)]">
                <Calculator size={14} /> Modo local · sem API
              </div>
              <h1 className="text-3xl font-semibold tracking-tight">Precificação de marketplaces</h1>
              <p className="mt-2 max-w-2xl text-sm text-[var(--color-text-secondary)]">
                Calcule preços seguros para Mercado Livre e Shopee. Nenhum anúncio é alterado automaticamente.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <input ref={fileRef} type="file" accept=".csv,.xlsx" className="hidden"
                onChange={(event) => { const file = event.target.files?.[0]; if (file) void importFile(file); }} />
              <button type="button" onClick={() => fileRef.current?.click()} className="inline-flex items-center gap-2 rounded-xl border border-[var(--color-border)] px-4 py-2.5 text-sm hover:bg-[var(--color-bg-secondary)]">
                <Upload size={16} /> Importar CSV/Excel
              </button>
              <button type="button" onClick={addProduct} className="inline-flex items-center gap-2 rounded-xl bg-[var(--color-accent)] px-4 py-2.5 text-sm font-medium text-[var(--color-on-accent)]">
                <Plus size={16} /> Novo produto
              </button>
            </div>
          </div>
        </section>

        <section className="grid gap-3 sm:grid-cols-3">
          <article className="hud-panel p-4"><p className="hud-label">PRODUTOS</p><p className="mt-1 text-2xl font-semibold">{state.products.length}</p></article>
          <article className="hud-panel p-4"><p className="hud-label">ABAIXO DO MÍNIMO</p><p className="mt-1 text-2xl font-semibold" style={{ color: belowMinimumCount ? 'var(--color-error)' : 'var(--color-success)' }}>{belowMinimumCount}</p></article>
          <article className="hud-panel p-4"><p className="hud-label">CADASTROS INCOMPLETOS</p><p className="mt-1 text-2xl font-semibold">{invalidSkuCount}</p></article>
        </section>

        <section className="grid min-h-[540px] gap-5 xl:grid-cols-[280px_1fr]">
          <aside className="hud-panel flex flex-col overflow-hidden">
            <div className="border-b border-[var(--color-border)] p-4">
              <h2 className="font-medium">Produtos cadastrados</h2>
              <p className="mt-1 text-xs text-[var(--color-text-tertiary)]">Salvos neste computador</p>
            </div>
            <div className="max-h-[610px] flex-1 overflow-y-auto p-2">
              {state.products.map((product) => (
                <button key={product.id} type="button" onClick={() => setSelectedId(product.id)}
                  className="mb-1 w-full rounded-xl p-3 text-left transition"
                  style={{ background: product.id === selected.id ? 'var(--color-accent-subtle)' : 'transparent', border: product.id === selected.id ? '1px solid var(--color-accent)' : '1px solid transparent' }}>
                  <span className="block truncate text-sm font-medium">{product.name || 'Sem nome'}</span>
                  <span className="mt-1 block truncate text-xs text-[var(--color-text-tertiary)]">{product.sku || 'Sem SKU'} · {money.format(product.currentPrice || 0)}</span>
                </button>
              ))}
            </div>
          </aside>

          <div className="flex flex-col gap-5">
            <section className="hud-panel p-5 md:p-6">
              <div className="mb-5 flex items-center justify-between gap-3">
                <div><p className="hud-label">CADASTRO MANUAL</p><h2 className="mt-1 text-lg font-semibold">Dados do produto</h2></div>
                <button type="button" onClick={deleteProduct} disabled={state.products.length === 1}
                  className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs text-[var(--color-error)] disabled:cursor-not-allowed disabled:opacity-30">
                  <Trash2 size={15} /> Excluir
                </button>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <label className="grid gap-1.5 text-xs text-[var(--color-text-secondary)]">SKU
                  <input value={selected.sku} onChange={(event) => updateProduct({ sku: event.target.value })} className="rounded-lg border border-[var(--color-input-border)] bg-[var(--color-input-bg)] px-3 py-2 text-sm outline-none focus:border-[var(--color-accent)]" />
                </label>
                <label className="grid gap-1.5 text-xs text-[var(--color-text-secondary)]">Nome do produto
                  <input value={selected.name} onChange={(event) => updateProduct({ name: event.target.value })} className="rounded-lg border border-[var(--color-input-border)] bg-[var(--color-input-bg)] px-3 py-2 text-sm outline-none focus:border-[var(--color-accent)]" />
                </label>
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <NumberField label="Custo do produto" value={selected.productCost} onChange={(v) => updateProduct({ productCost: v })} suffix="R$" />
                <NumberField label="Embalagem" value={selected.packagingCost} onChange={(v) => updateProduct({ packagingCost: v })} suffix="R$" />
                <NumberField label="Outros custos" value={selected.operationalCost} onChange={(v) => updateProduct({ operationalCost: v })} suffix="R$" />
                <NumberField label="Preço atual" value={selected.currentPrice} onChange={(v) => updateProduct({ currentPrice: v })} suffix="R$" />
                <NumberField label="Margem desejada" value={selected.desiredMarginPercent} onChange={(v) => updateProduct({ desiredMarginPercent: v })} suffix="%" />
                <NumberField label="Margem promocional" value={selected.promotionalMarginPercent} onChange={(v) => updateProduct({ promotionalMarginPercent: v })} suffix="%" />
              </div>
              <div className="mt-4 flex items-center gap-2 text-xs text-[var(--color-text-tertiary)]"><Save size={14} /> Alterações salvas automaticamente neste computador.</div>
            </section>

            <section className="hud-panel p-5 md:p-6">
              <div className="mb-5"><p className="hud-label">TAXAS CONFIGURÁVEIS</p><h2 className="mt-1 text-lg font-semibold">Regras por marketplace</h2><p className="mt-1 text-xs text-[var(--color-text-tertiary)]">Começam zeradas: informe as taxas mostradas na sua conta.</p></div>
              <div className="grid gap-4 lg:grid-cols-2">
                {(['mercado_livre', 'shopee'] as MarketplaceId[]).map((marketplace) => (
                  <MarketplaceSettings key={marketplace} marketplace={marketplace} value={state.fees[marketplace]}
                    onChange={(value) => setState((current) => ({ ...current, fees: { ...current.fees, [marketplace]: value } }))} />
                ))}
              </div>
            </section>

            {error ? (
              <section className="hud-panel flex items-center gap-3 border-[var(--color-error)] p-5 text-sm text-[var(--color-error)]"><AlertTriangle size={20} /> {error}</section>
            ) : comparison && (
              <section className="hud-panel p-5 md:p-6">
                <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
                  <div><p className="hud-label">COMPARAÇÃO</p><h2 className="mt-1 text-lg font-semibold">Mercado Livre × Shopee</h2></div>
                  <span className="rounded-full bg-[var(--color-accent-subtle)] px-3 py-1.5 text-xs text-[var(--color-accent)]">Menor recomendado: {marketplaceLabels[comparison.lowestRecommendedMarketplace]} ({money.format(comparison.recommendedDifference)} de diferença)</span>
                </div>
                <div className="grid gap-4 lg:grid-cols-2">
                  {(['mercado_livre', 'shopee'] as MarketplaceId[]).map((marketplace) => {
                    const result = comparison[marketplace];
                    return (
                      <article key={marketplace} className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-5">
                        <div className="flex items-center justify-between gap-3"><h3 className="font-semibold">{marketplaceLabels[marketplace]}</h3><span className="text-xs font-medium" style={{ color: alertColors[result.alert] }}>{alertLabels[result.alert]}</span></div>
                        <div className="mt-5 grid grid-cols-3 gap-2 text-center">
                          <div><p className="text-[10px] uppercase text-[var(--color-text-tertiary)]">Mínimo</p><p className="mt-1 font-semibold">{money.format(result.minimumPrice)}</p></div>
                          <div><p className="text-[10px] uppercase text-[var(--color-text-tertiary)]">Promocional</p><p className="mt-1 font-semibold">{money.format(result.promotionalPrice)}</p></div>
                          <div><p className="text-[10px] uppercase text-[var(--color-text-tertiary)]">Recomendado</p><p className="mt-1 font-semibold text-[var(--color-accent)]">{money.format(result.recommendedPrice)}</p></div>
                        </div>
                        <div className="mt-5 grid grid-cols-2 gap-3 border-t border-[var(--color-border)] pt-4 text-sm">
                          <div><p className="text-xs text-[var(--color-text-tertiary)]">Lucro líquido atual</p><p className="mt-1 font-medium">{result.currentProfit === null ? '—' : money.format(result.currentProfit)}</p></div>
                          <div><p className="text-xs text-[var(--color-text-tertiary)]">Margem real atual</p><p className="mt-1 font-medium">{result.currentMarginPercent === null ? '—' : `${result.currentMarginPercent.toFixed(2)}%`}</p></div>
                        </div>
                      </article>
                    );
                  })}
                </div>
              </section>
            )}

            <section className="hud-panel flex flex-col items-start gap-3 p-5 sm:flex-row sm:items-center">
              <FileSpreadsheet size={22} className="text-[var(--color-accent)]" />
              <div><h3 className="text-sm font-medium">Modelo para importação</h3><p className="mt-1 text-xs leading-5 text-[var(--color-text-tertiary)]">Use as colunas: SKU, Nome, Custo, Embalagem, Outros custos, Margem desejada, Margem promocional e Preço atual. Limite de 1.000 produtos.</p></div>
            </section>
          </div>
        </section>
      </main>
    </div>
  );
}

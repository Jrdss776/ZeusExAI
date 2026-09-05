import { describe, expect, it } from 'vitest';
import {
  calculatePricing,
  compareMarketplaces,
  emptyFees,
  mapImportedRows,
  parseCsv,
  type ManualProduct,
} from './marketplace-pricing';

const product: ManualProduct = {
  id: '1', sku: 'SKU-1', name: 'Produto', productCost: 50,
  packagingCost: 3, operationalCost: 2, desiredMarginPercent: 20,
  promotionalMarginPercent: 10, currentPrice: 100,
};

const fees = {
  ...emptyFees(), commissionPercent: 12, paymentFeePercent: 2,
  taxPercent: 4, advertisingPercent: 2, fixedFee: 3, shippingCost: 7,
};

describe('precificação sem API', () => {
  it('calcula mínimo, promocional, recomendado, lucro e margem real', () => {
    const result = calculatePricing(product, 'mercado_livre', fees);
    expect(result.minimumPrice).toBe(81.25);
    expect(result.promotionalPrice).toBe(92.86);
    expect(result.recommendedPrice).toBe(108.34);
    expect(result.currentProfit).toBe(15);
    expect(result.currentMarginPercent).toBe(15);
    expect(result.alert).toBe('abaixo_recomendado');
  });

  it('alerta preço abaixo do mínimo', () => {
    expect(calculatePricing({ ...product, currentPrice: 80 }, 'shopee', fees).alert).toBe('abaixo_minimo');
  });

  it('compara Mercado Livre e Shopee', () => {
    const comparison = compareMarketplaces(product, {
      mercado_livre: fees,
      shopee: { ...fees, commissionPercent: 8 },
    });
    expect(comparison.lowestRecommendedMarketplace).toBe('shopee');
    expect(comparison.recommendedDifference).toBe(6.77);
  });

  it('rejeita margem matematicamente inviável', () => {
    expect(() => calculatePricing(
      { ...product, desiredMarginPercent: 40 },
      'shopee',
      { ...fees, commissionPercent: 40, paymentFeePercent: 10, taxPercent: 10, advertisingPercent: 0 },
    )).toThrow('inviável');
  });

  it('importa CSV brasileiro com separador e vírgula decimal', () => {
    const [row] = parseCsv([
      'SKU;Nome;Custo;Embalagem;Outros custos;Margem desejada;Margem promocional;Preço atual',
      'ABC;Produto A;50,90;2,50;1;25;10;99,90',
    ].join('\n'));
    expect(row.sku).toBe('ABC');
    expect(row.productCost).toBe(50.9);
    expect(row.currentPrice).toBe(99.9);
  });

  it('mapeia colunas equivalentes vindas do Excel', () => {
    const [row] = mapImportedRows([{ codigo: 'X1', produto: 'Produto X', custo_produto: 30 }]);
    expect(row).toMatchObject({ sku: 'X1', name: 'Produto X', productCost: 30 });
  });

  it('preserva os campos normalizados retornados pelo importador local', () => {
    const [row] = mapImportedRows([{
      sku: 'X2', name: 'Produto Excel', productCost: 45.5,
      packagingCost: 2, desiredMarginPercent: 25, currentPrice: 79.9,
    }]);
    expect(row).toMatchObject({ productCost: 45.5, packagingCost: 2, desiredMarginPercent: 25, currentPrice: 79.9 });
  });

  it('rejeita linhas sem identificação', () => {
    expect(() => mapImportedRows([{ produto: 'Sem SKU', custo: 10 }])).toThrow('SKU e nome');
  });
});
